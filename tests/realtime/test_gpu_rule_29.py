"""WP29: Admission, Profile und Lebenszyklus ohne GPU oder Modelle."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from sirens.contracts import Ablehnung
from sirens.realtime.gpu_manager import GPUManager, Priority, GIB, ManagedClaudeStarter
from sirens.realtime.model_registry import ModelRegistry
from sirens.realtime.telemetry import read_gpu, Telemetry
from sirens.realtime.worker_supervisor import SessionWorkers


class GPU29(unittest.TestCase):
    def manager(self):
        return GPUManager(lambda: read_gpu(lambda *a, **kw: SimpleNamespace(
            stdout="Test RTX, 16384, 1024, 15360, 0, 40\n")))

    def test_claude_exclusive_and_fallback(self):
        gpu = self.manager()
        lease = gpu.acquire(GIB, Priority.AUDIO, lambda: False, user_action=True)
        with self.assertRaises(Ablehnung) as exc:
            gpu.acquire_claude()
        self.assertEqual(exc.exception.code, "busy_gpu")
        gpu.release(lease)
        for manager in (gpu, GPUManager(lambda: Telemetry())):
            claude = manager.acquire_claude()
            self.assertEqual(manager.lease_snapshot()[0]["owner"], "claude")
            with self.assertRaises(Ablehnung):
                manager.acquire(GIB, Priority.AUDIO, lambda: True, user_action=True)
            manager.set_profile("Eco")
            manager.release(claude)
            self.assertEqual(manager.leases, ())

    def test_claude_followup_and_busy(self):
        gpu = self.manager()
        with tempfile.TemporaryDirectory() as tmp:
            cfg = SimpleNamespace(claude_start=True, data_dir=Path(tmp))
            marker = Path(tmp) / "runs"
            cmd = [sys.executable, "-c",
                   "import pathlib,sys,time; sys.stdin.read(); "
                   "p=pathlib.Path(sys.argv[1]); "
                   "p.write_text((p.read_text() if p.exists() else '')+'x'); "
                   "time.sleep(.3)", str(marker)]
            starter = ManagedClaudeStarter(cfg, lambda: gpu, threading.RLock(), cmd=cmd, cwd=tmp)
            lease = gpu.acquire(GIB, Priority.AUDIO, lambda: False, user_action=True)
            self.assertFalse(starter.starten()["laeuft"])
            self.assertTrue(starter.zustand()["letzter"]["fehler"])
            with self.assertRaises(Ablehnung) as exc:
                starter.starten(raise_busy=True)
            self.assertEqual(exc.exception.code, "busy_gpu")
            gpu.release(lease)
            self.assertTrue(starter.starten()["laeuft"])
            first = gpu.leases[0]
            starter.starten()
            self.assertEqual(gpu.leases, (first,))
            self.assertTrue(starter.warten(timeout=10))
            self.assertEqual(marker.read_text(), "xx")
            self.assertEqual(gpu.leases, ())

    def test_profiles_and_session_cleanup(self):
        gpu = self.manager()
        pool = SessionWorkers(ModelRegistry(env={}, mock_enabled=True), gpu)
        self.addCleanup(pool.close)
        with self.assertRaises(Ablehnung):
            pool.preload("mock")
        worker = pool.preload("mock", {"gain": 0.5}, user_action=True)
        process = worker.worker.process
        self.assertIs(pool.preload("mock", user_action=True), worker)
        self.assertTrue(worker.request("health")["loaded"])
        self.assertEqual(worker.queue_limit, 4)
        gpu.set_profile("Neural")
        self.assertEqual(worker.queue_limit, 8)
        leases = [gpu.acquire(GIB, Priority.AUDIO, lambda: False, user_action=True)
                  for _ in range(2)]
        with self.assertRaises(Ablehnung):
            gpu.set_profile("Eco")
        for lease in leases:
            gpu.release(lease)
        gpu.set_profile("Eco")
        self.assertEqual(worker.queue_limit, 2)
        with self.assertRaises(Ablehnung):
            gpu.acquire(GIB, Priority.AUDIO, lambda: True, user_action=True)
        pool.close()
        self.assertIsNotNone(process.poll())
        with self.assertRaises(Ablehnung):
            pool.preload("mock", user_action=True)
