"""Companion ohne Netz, Modellgewichte oder GPU."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
import wave

from workers.magenta.adapter import Companion, HOP, RATE
from sirens.realtime.model_registry import ModelRegistry

ROOT = Path(__file__).resolve().parents[2]


def pcm(value, frames=HOP):
    return struct.pack("<ff", value, value) * frames


class FakeModel:
    """Nachbau des Backend-Vertrags mit fortlaufendem Zustand."""
    def __init__(self):
        self.closed = False
        self.states = []

    def embed(self, reference):
        return struct.unpack_from("<f", reference)[0]

    def generate(self, conditioning, state):
        self.states.append(state)
        return pcm(conditioning + (state or 0) / 100), (state or 0) + 1

    def close(self):
        self.closed = True


class TestMagentaCompanion(unittest.TestCase):
    def setUp(self):
        self.models = []

        def factory():
            model = FakeModel()
            self.models.append(model)
            return model
        self.adapter = Companion(factory)
        self.addCleanup(self.adapter.unload)

    def test_lifecycle_reference_and_gain(self):
        with self.assertRaises(RuntimeError):
            self.adapter.process()
        self.adapter.load(gain=0.5)
        self.assertTrue(self.adapter.health()["loaded"])
        self.assertAlmostEqual(struct.unpack_from("<f", self.adapter.process(pcm(.4)))[0], .2)
        self.assertAlmostEqual(struct.unpack_from("<f", self.adapter.process())[0], .205)
        self.assertAlmostEqual(struct.unpack_from("<f", self.adapter.process(pcm(.8)))[0], .41)
        self.assertEqual(self.models[0].states, [None, 1, 2])
        self.adapter.cancel()
        with self.assertRaises(RuntimeError):
            self.adapter.process()
        self.adapter.load()
        self.assertTrue(self.models[0].closed)
        self.adapter.process(pcm(.3))
        self.assertEqual(self.models[1].states, [None])

    def test_bypass_and_unload(self):
        self.adapter.load(bypass=1)
        self.assertEqual(self.adapter.process(pcm(.5)), bytes(HOP * 8))
        self.assertEqual(self.models[0].states, [])
        self.adapter.unload()
        self.assertTrue(self.models[0].closed)
        self.assertFalse(self.adapter.health()["loaded"])

    def test_invalid_inputs(self):
        for value in (float("nan"), -1, True, 3):
            with self.assertRaises(ValueError):
                self.adapter.load(gain=value)
        self.adapter.load()
        for raw in (b"x", pcm(float("inf")), pcm(2), bytes(1024 * 1024 + 8)):
            with self.assertRaises(ValueError):
                self.adapter.process(raw)

    def test_cancel_during_generation(self):
        entered, release = threading.Event(), threading.Event()
        errors = []
        self.adapter.load()
        model = self.models[0]
        original = model.generate

        def slow(*args):
            entered.set()
            if not release.wait(3):
                raise RuntimeError("Test-Timeout")
            return original(*args)
        model.generate = slow

        def run():
            try:
                self.adapter.process(pcm(.4))
            except RuntimeError as exc:
                errors.append(str(exc))
        thread = threading.Thread(target=run)
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.adapter.cancel()
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, ["Companion gestoppt"])
        self.assertFalse(self.adapter.health()["busy"])

    def test_registry_gate_disabled(self):
        registry = ModelRegistry(root=ROOT, env={"SIRENS_RT_MAGENTA_PYTHON": sys.executable})
        cap = next(c for c in registry.capabilities() if c["id"] == "magenta")
        self.assertFalse(cap["available"])
        self.assertFalse(cap["mock"])
        self.assertEqual(cap["mode"], "offline")
        self.assertEqual(cap["sample_rates"], [RATE])

    def test_ipc_control_lifecycle(self):
        def frame(kind, rid, payload):
            body = json.dumps(dict(version=1, type=kind, request_id=rid, payload=payload)).encode()
            return struct.pack("<I", len(body)) + body

        code = ("import sys; from workers.magenta.worker import serve; "
                "from workers.magenta.adapter import Companion; "
                "serve(Companion(lambda: type('Fake', (), {'close':lambda self:None})()), "
                "{'available':False}, sys.stdin.buffer, sys.stdout.buffer)")
        kinds = ["probe", "load", "health", "cancel", "health", "unload"]
        output = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                                input=b"".join(frame(k, str(i), {}) for i, k in enumerate(kinds)),
                                capture_output=True, timeout=10, check=True).stdout
        replies = {}
        while output:
            size, = struct.unpack_from("<I", output)
            msg = json.loads(output[4:4+size])
            output = output[4+size:]
            if msg["type"] != "heartbeat":
                self.assertEqual(msg["type"], "result")
                replies[msg["request_id"]] = msg["payload"]
        self.assertEqual(len(replies), len(kinds))
        self.assertFalse(replies["0"]["available"])
        self.assertTrue(replies["2"]["loaded"])
        self.assertFalse(replies["4"]["loaded"])

    def test_installer_without_opt_in(self):
        from workers.magenta import install
        with patch.object(install, "obtain") as obtain, patch.object(install.subprocess, "run") as run:
            self.assertEqual(install.main([]), 0)
            obtain.assert_not_called()
            run.assert_not_called()
        items = install.manifest()
        self.assertEqual(len(items), 6)
        for item in items:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(item["size_bytes"], 0)

    def test_benchmark_short_mock(self):
        from benchmarks.companion import messen
        from benchmarks import result

        class Sampler:
            proc_peak = gpu_peak = None

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                pass

        machine = {k: None for k in
                   ("os", "python", "node", "ffmpeg", "gpus", "wsl", "disk", "git", "notes")}
        with TemporaryDirectory() as tmp, patch.object(messen.runner, "Sampler", Sampler), \
                patch.object(messen.baseline, "collect", return_value=machine):
            directory = Path(tmp) / "result"
            data = messen.run(FakeModel, directory, 1)
            self.assertEqual(result.read(directory / "result.json"), data)
            self.assertEqual(data["gate"], "nicht_gemessen")
            self.assertTrue(data["profil"]["stop_ok"])
            with wave.open(str(directory / "companion.wav"), "rb") as wav:
                self.assertEqual(wav.getnframes(), RATE)
                self.assertEqual(wav.getnchannels(), 2)


if __name__ == "__main__":
    unittest.main()
