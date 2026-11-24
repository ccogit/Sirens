import os
import sys
import tempfile
from pathlib import Path
import threading
import unittest
from types import SimpleNamespace

from sirens.contracts import Ablehnung
from sirens.production.contracts import ContractError
from sirens.production.gpu import GPUAdapter
from sirens.production.jobs import Cancelled, run_file_worker
from sirens.realtime.gpu_manager import GIB, GPUManager


class ProductionLeaseTests(unittest.TestCase):
    def manager(self):
        return GPUManager(telemetry=lambda: SimpleNamespace(available=True, free=24*GIB),
                          reserve_bytes=2*GIB)

    def test_shared_lease_and_claude(self):
        manager = self.manager()
        adapter = GPUAdapter(manager, threading.RLock())
        claude = manager.acquire_claude()
        try:
            with self.assertRaises(Ablehnung):
                with adapter.worker_lease(GIB, user_action=True, stopped=lambda: True):
                    self.fail("must not run alongside Claude")
        finally:
            manager.release(claude)
        with adapter.worker_lease(GIB, user_action=True, stopped=lambda: True):
            with self.assertRaises(Ablehnung):
                manager.acquire_claude()
            with self.assertRaises(Ablehnung):
                with adapter.worker_lease(GIB, user_action=True, stopped=lambda: True):
                    self.fail("must not run a second production worker")
        self.assertEqual(manager.leases, ())

    def test_no_consent_and_unconfirmed_stop(self):
        manager = self.manager()
        adapter = GPUAdapter(manager, threading.RLock())
        with self.assertRaises(ContractError):
            with adapter.worker_lease(GIB, user_action=False, stopped=lambda: True):
                pass
        with self.assertRaises(ContractError):
            with adapter.worker_lease(GIB, user_action=True, stopped=lambda: False):
                pass
        self.assertEqual(len(manager.leases), 1)
        with self.assertRaises(Ablehnung):
            manager.acquire_claude()

    def test_exception_releases_after_stop(self):
        manager = self.manager()
        adapter = GPUAdapter(manager, threading.RLock())
        with self.assertRaises(RuntimeError):
            with adapter.worker_lease(GIB, user_action=True, stopped=lambda: True):
                raise RuntimeError("crash")
        self.assertEqual(manager.leases, ())


@unittest.skipUnless(os.name == "posix", "POSIX resource limits")
class WorkerProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workers = self.root / "workers"
        self.worker = self.workers / "test"
        self.worker.mkdir(parents=True)
        (self.worker / "python").symlink_to(sys.executable)
        self.run_dir = self.root / "run"
        self.run_dir.mkdir()

    def execute(self, script, *, timeout=3, check_cancel=lambda: None):
        (self.worker / "job.py").write_text(script, encoding="utf-8")
        run_file_worker(self.workers, "test", "python", "job.py", self.run_dir,
                        timeout=timeout, cpu_seconds=2, memory_bytes=256*1024**2,
                        check_cancel=check_cancel)

    def test_process_and_resource_limits(self):
        self.execute("import resource, pathlib, sys\n"
                     "assert resource.getrlimit(resource.RLIMIT_CPU) == (2, 2)\n"
                     "assert resource.getrlimit(resource.RLIMIT_AS) == (268435456, 268435456)\n"
                     "pathlib.Path(sys.argv[1], 'done').write_text('ok')\n")
        self.assertEqual((self.run_dir / "done").read_text(), "ok")

    def test_crash_timeout_cancel(self):
        with self.assertRaisesRegex(ContractError, "worker exit code 7"):
            self.execute("raise SystemExit(7)")
        with self.assertRaisesRegex(ContractError, "deadline"):
            self.execute("import time; time.sleep(20)", timeout=0.15)
        count = 0
        def cancel():
            nonlocal count
            count += 1
            if count > 2:
                raise Cancelled()
        with self.assertRaises(Cancelled):
            self.execute("import time; time.sleep(20)", check_cancel=cancel)
