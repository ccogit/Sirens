import subprocess
import unittest
from types import SimpleNamespace

from sirens.contracts import Ablehnung
from sirens.realtime.gpu_manager import GPUManager, Priority, GIB
from sirens.realtime.telemetry import read_gpu, Telemetry, MIB
from sirens.realtime.schema import validate


class GPU(unittest.TestCase):
    def test_telemetry(self):
        def run(command, **kwargs):
            self.assertEqual(command[0], "nvidia-smi")
            self.assertTrue(kwargs["check"])
            return SimpleNamespace(stdout="RTX Test, 16384, 4096, 12288, 15, 45\n")
        data = read_gpu(run)
        self.assertEqual((data.total, data.used, data.free), (16384*MIB, 4096*MIB, 12288*MIB))
        validate("telemetry", data.as_dict())
        for output in ("", "No devices were found", "GPU, N/A, 0, 0, 0, 0", "GPU, 2, 3, 0, 0, 0"):
            data = read_gpu(lambda *a, **kw: SimpleNamespace(stdout=output))
            self.assertFalse(data.available)
            validate("telemetry", data.as_dict())
        def missing(*a, **kw):
            raise FileNotFoundError()
        self.assertFalse(read_gpu(missing).available)

    def test_leases_and_external_load(self):
        free = [8*GIB]
        manager = GPUManager(lambda: Telemetry("GPU", 16*GIB, 16*GIB-free[0], free[0], 0, 40))
        stopped = []
        low = manager.acquire(4*GIB, Priority.VISUALS, lambda: stopped.append("low") or True, user_action=True)
        with self.assertRaises(Ablehnung) as ctx:
            manager.acquire(2*GIB, Priority.VISUALS, lambda: True, user_action=True)
        self.assertEqual(ctx.exception.code, "busy_gpu")
        high = manager.acquire(4*GIB, Priority.AUDIO, lambda: stopped.append("high") or True, user_action=True)
        self.assertEqual(stopped, ["low"])
        self.assertEqual(manager.leases, (high,))
        manager.release(low)
        free[0] = GIB
        self.assertFalse(manager.reconcile())
        self.assertEqual(stopped, ["low", "high"])
        self.assertFalse(manager.leases)

    def test_no_gpu_no_action_and_failed_unload(self):
        manager = GPUManager(lambda: Telemetry())
        with self.assertRaises(Ablehnung) as ctx:
            manager.acquire(1, Priority.AUDIO, lambda: True, user_action=True)
        self.assertEqual(ctx.exception.code, "busy_gpu")
        with self.assertRaises(Ablehnung):
            manager.acquire(1, Priority.AUDIO, lambda: True)
        manager = GPUManager(lambda: Telemetry("GPU", 4*GIB, 0, 4*GIB, 0, 40))
        low = manager.acquire(GIB, Priority.BACKGROUND, lambda: False, user_action=True)
        with self.assertRaises(Ablehnung):
            manager.acquire(GIB, Priority.AUDIO, lambda: True, user_action=True)
        self.assertEqual(manager.leases, (low,))
