import struct
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from sirens.contracts import Ablehnung
from sirens.realtime.model_registry import ModelRegistry
from sirens.realtime.worker_supervisor import WorkerSupervisor
from sirens.realtime.schemas import validate


class Workers(unittest.TestCase):
    def setUp(self):
        self.registry = ModelRegistry(env={}, mock_enabled=True)
        self.supervisor = WorkerSupervisor(self.registry, "mock", max_pending=2)
        self.addCleanup(self.supervisor.close)
        self.supervisor.start(user_action=True)
        self.processes = [self.supervisor.worker.process]
        self.addCleanup(self.check_cleanup)
        self.supervisor.request("load", {"gain": 0.5})
        self.supervisor.request("warmup")

    def check_cleanup(self):
        if self.supervisor.worker.process:
            self.processes.append(self.supervisor.worker.process)
        self.supervisor.close()
        for proc in self.processes:
            self.assertIsNotNone(proc.poll())

    def test_heartbeat_and_persistent_process(self):
        initial = self.supervisor.worker.last_heartbeat
        validate("capability", self.supervisor.request("probe"))
        self.assertTrue(self.supervisor.request("health")["loaded"])
        end = time.monotonic() + 2.5
        while self.supervisor.worker.last_heartbeat <= initial and time.monotonic() < end:
            time.sleep(0.05)
        self.assertGreater(self.supervisor.worker.last_heartbeat, initial)
        _, raw = self.supervisor.request("process", audio=struct.pack("<ff", 1, -1))
        self.assertEqual(struct.unpack("<ff", raw), (0.5, -0.5))
        self.assertIs(self.supervisor.worker.process, self.processes[0])
        self.supervisor.request("unload")
        self.assertFalse(self.supervisor.request("health")["loaded"])

    def test_timeout_restart_and_crash_limit(self):
        with self.assertRaises(Ablehnung) as ctx:
            self.supervisor.request("process", {"delay_seconds": 1}, timeout=0.15)
        self.assertEqual(ctx.exception.code, "deadline_missed")
        self.assertIsNotNone(self.processes[0].poll())
        self.assertFalse(self.supervisor.request("health")["loaded"])
        self.processes.append(self.supervisor.worker.process)
        self.supervisor.request("load")
        with self.assertRaises(Ablehnung):
            self.supervisor.request("process", {"crash": True})
        with self.assertRaises(Ablehnung):
            self.supervisor.request("health")
        self.assertEqual(self.supervisor.restarts, 1)

    def test_oom_and_rejection(self):
        with self.assertRaises(Ablehnung) as ctx:
            self.supervisor.request("process", {"memory_bytes": 10, "memory_limit_bytes": 1})
        self.assertEqual(ctx.exception.code, "busy_gpu")
        self.assertTrue(self.supervisor.request("health")["loaded"])
        with self.assertRaises(Ablehnung):
            self.supervisor.request("load", {"path": "../model"})
        with self.assertRaises(Ablehnung):
            WorkerSupervisor(self.registry, "../mock")
        self.assertEqual(ModelRegistry(env={}, mock_enabled=False).capabilities(), [])
        other = WorkerSupervisor(self.registry, "mock")
        self.addCleanup(other.close)
        with self.assertRaises(Ablehnung):
            other.start()

    def test_concurrent_and_cancel(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(self.supervisor.request, "process", {"delay_seconds": 0.3})
            b = pool.submit(self.supervisor.request, "health")
            a.result(timeout=5)
            self.assertTrue(b.result(timeout=5)["loaded"])
            future = pool.submit(self.supervisor.request, "process", {"delay_seconds": 10})
            end = time.monotonic() + 2
            while not self.supervisor.serial.locked() and time.monotonic() < end:
                time.sleep(0.01)
            self.assertTrue(self.supervisor.serial.locked())
            self.supervisor.cancel()
            with self.assertRaises(Ablehnung):
                future.result(timeout=5)
            self.assertIsNotNone(self.processes[0].poll())

    def test_bounded_queue(self):
        single = WorkerSupervisor(self.registry, "mock", max_pending=1)
        self.addCleanup(single.close)
        single.start(user_action=True)
        single.request("load")
        with ThreadPoolExecutor(max_workers=1) as pool:
            active = pool.submit(single.request, "process", {"delay_seconds": 10})
            end = time.monotonic() + 2
            while not single.serial.locked() and time.monotonic() < end:
                time.sleep(0.01)
            self.assertTrue(single.serial.locked())
            try:
                with self.assertRaises(Ablehnung) as ctx:
                    single.request("health")
                self.assertEqual(ctx.exception.code, "unavailable")
            finally:
                single.cancel()
            with self.assertRaises(Ablehnung):
                active.result(timeout=5)
