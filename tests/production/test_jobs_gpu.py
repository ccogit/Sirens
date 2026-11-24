import tempfile
import threading
import unittest
from types import SimpleNamespace

from sirens.contracts import Ablehnung
from sirens.production.contracts import ContractError
from sirens.production.gpu import GPUAdapter
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
