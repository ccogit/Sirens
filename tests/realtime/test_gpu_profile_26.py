"""Globale Profile begrenzen Leases zusätzlich zur Supervisor-Grenze."""
import unittest
from sirens.contracts import Ablehnung
from sirens.realtime.gpu_manager import GPUManager, Priority, GIB
from sirens.realtime.telemetry import Telemetry


class GPUProfile26(unittest.TestCase):
    def test_limits_and_safe_downgrade(self):
        manager = GPUManager(lambda: Telemetry("Test", 16*GIB, 0, 16*GIB, 0, 40))
        def acquire(**kwargs):
            return manager.acquire(GIB, Priority.AUDIO, lambda: True, user_action=True, **kwargs)

        manager.set_profile("Eco")
        with self.assertRaises(Ablehnung) as exc:
            acquire()
        self.assertEqual(exc.exception.code, "busy_gpu")
        manager.set_profile("Neural")
        first, second = acquire(), acquire()
        with self.assertRaises(Ablehnung):
            acquire()
        with self.assertRaises(Ablehnung):
            manager.set_profile("Performance")
        self.assertEqual(manager.profile, "Neural")
        manager.release(second)
        manager.set_profile("Training/Render")
        with self.assertRaises(Ablehnung):
            acquire()
        manager.release(first)
        manager.set_profile("Neural")
        first = acquire(max_leases=1)
        with self.assertRaises(Ablehnung):
            acquire(max_leases=1)
        manager.release(first)
        with self.assertRaises(Ablehnung):
            manager.set_profile([])
        self.assertEqual(manager.profile, "Neural")

    def test_neural_still_requires_telemetry(self):
        manager = GPUManager(lambda: Telemetry(), profile="Neural")
        with self.assertRaises(Ablehnung) as exc:
            manager.acquire(GIB, Priority.AUDIO, lambda: True, user_action=True)
        self.assertEqual(exc.exception.code, "busy_gpu")
