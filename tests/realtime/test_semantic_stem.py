"""Netz- und GPU-freie Tests für SAM-Dateijob mit nachgebautem Modell."""
import json
import subprocess
import sys
import struct
import tempfile
import threading
import unittest
import wave
from pathlib import Path

from workers.sam_audio.backend import SamBackend, verify_snapshot, PIN
from workers.sam_audio.adapter import Cancelled, encode, separate, split_sample
from workers.sam_audio.cache import SemanticCache, validate_assets
from sirens.realtime.model_registry import ModelRegistry

ROOT = Path(__file__).resolve().parents[2]


class Fake:
    def __init__(self, cancel=None):
        self.calls = []
        self.cancel = cancel

    def separate(self, mono, rate, prompt):
        self.calls.append(prompt)
        if self.cancel:
            self.cancel.set()
        return [x * 0.5 for x in mono]


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "song.wav"
        with wave.open(str(self.source), "wb") as w:
            w.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
            w.writeframes(encode([32767, -32768, 2400, -600, -300, 1000]*200))
        self.out = self.root / "out"
        self.out.mkdir()
        self.cancel = threading.Event()
        self.params = {"prompt": "bass"}

    def test_assets_and_cache(self):
        cache = SemanticCache(self.root / "cache", self.root / "music")
        digest, key, hit = cache.lookup(self.source, "revision-1", self.params)
        self.assertIsNone(hit)
        model = Fake()
        self.assertEqual(separate(model, self.source, self.out, self.params, self.cancel),
                         ["target.wav", "residual.wav"])
        self.assertEqual(model.calls, ["bass"])
        self.assertTrue(validate_assets(self.source, self.out))
        target = cache.publish(self.source, self.out, digest, "revision-1", self.params, self.cancel)
        self.assertEqual(cache.lookup(self.source, "revision-1", self.params), (digest, key, target))
        self.assertIsNone(cache.lookup(self.source, "revision-2", self.params)[2])
        self.assertIsNone(cache.lookup(self.source, "revision-1", {"prompt": "drums"})[2])

    def test_cancel_and_invalid(self):
        with self.assertRaises(Cancelled):
            separate(Fake(self.cancel), self.source, self.out, self.params, self.cancel)
        self.assertEqual(list(self.out.iterdir()), [])
        with self.assertRaises(ValueError):
            separate(Fake(), self.source, self.out, {"prompt": "../", "source": "x"}, threading.Event())
        self.assertEqual(list(self.out.iterdir()), [])

    def test_extremes(self):
        for x in (-32768, 32767, 0):
            for y in (-2, 2, 0, 0.01):
                a, b = split_sample(x, y)
                self.assertEqual(a+b, x)
                self.assertTrue(-32768 <= a <= 32767 and -32768 <= b <= 32767)

    def test_registry_disabled_even_with_interpreter(self):
        for env in ({}, {"SIRENS_RT_SAM_AUDIO_PYTHON": sys.executable}):
            reg = ModelRegistry(ROOT, env=env)
            cap = next(c for c in reg.capabilities() if c["id"] == "sam_audio")
            self.assertFalse(cap["available"])
            self.assertFalse(cap["mock"])

    def test_ipc_lifecycle(self):
        code = ("from workers.sam_audio.worker import main\n"
                "class Model:\n"
                " def separate(self, mono, rate, prompt): return [v/2 for v in mono]\n"
                "main(Model)\n")
        with subprocess.Popen([sys.executable, "-u", "-c", code], cwd=ROOT,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL) as p:
            try:
                def request(kind, payload=None):
                    raw = json.dumps(dict(version=1, request_id=kind, type=kind,
                                          payload=payload or {})).encode()
                    p.stdin.write(struct.pack("<I", len(raw))+raw)
                    p.stdin.flush()
                    while True:
                        header = p.stdout.read(4)
                        self.assertEqual(len(header), 4)
                        msg = json.loads(p.stdout.read(struct.unpack("<I", header)[0]))
                        if msg["type"] != "heartbeat":
                            self.assertEqual(msg["request_id"], kind)
                            return msg
                self.assertFalse(request("probe")["payload"]["available"])
                self.assertEqual(request("load")["type"], "result")
                payload = dict(job_id="test", source=str(self.source), out_dir=str(self.out),
                               params=self.params)
                self.assertEqual(request("file_job", payload)["payload"]["files"],
                                 ["target.wav", "residual.wav"])
                self.assertTrue(validate_assets(self.source, self.out))
                self.assertEqual(request("cancel")["type"], "result")
                self.assertEqual(request("file_job", payload)["type"], "error")
                self.assertEqual(request("unload")["type"], "result")
                self.assertFalse(request("health")["payload"]["loaded"])
            finally:
                p.kill()
                p.wait(timeout=5)

    def test_model_interface(self):
        # Dieselbe Schnittstelle wie SAMAudioProcessor / SAMAudio.separate.
        from contextlib import nullcontext
        from types import SimpleNamespace
        class Tensor:
            def __init__(self, values):
                self.values = list(values)
            def unsqueeze(self, axis): return self
            def detach(self): return self
            def cpu(self): return self
            def reshape(self, *args): return self
            def numel(self): return len(self.values)
            def __getitem__(self, sl): return Tensor(self.values[sl])
            def tolist(self): return self.values
            def to(self, device): return self
        calls = []
        class Processor:
            audio_sampling_rate = 44100
            def __call__(self, *, audios, descriptions):
                calls.append(descriptions)
                return audios[0]
        class Model:
            def separate(self, batch, *, predict_spans, reranking_candidates):
                calls.append((predict_spans, reranking_candidates))
                return SimpleNamespace(target=[batch])
        backend = SamBackend.__new__(SamBackend)
        backend.processor, backend.model = Processor(), Model()
        backend.device = "cpu"
        backend.torch = SimpleNamespace(float32=None, tensor=lambda values, **kw: Tensor(values),
                                        inference_mode=nullcontext, manual_seed=lambda seed: None)
        backend.audio = SimpleNamespace(functional=SimpleNamespace(resample=lambda t, a, b: t))
        self.assertEqual(backend.separate([.25, -.25], 44100, "voice"), [.25, -.25])
        self.assertEqual(calls, [["voice"], (False, 1)])

    def test_snapshot_rejects_unverified_or_changed_files(self):
        import hashlib
        snapshot = self.root / "snapshot"
        snapshot.mkdir()
        files = {}
        for name in ("checkpoint.pt", "config.json"):
            # Beliebige Bytes, keine echten Gewichte.
            data = name.encode()
            (snapshot / name).write_bytes(data)
            files[name] = hashlib.sha256(data).hexdigest()
        receipt = self.root / "receipt.json"
        info = dict(code_pin=PIN, offline_audited=False, snapshot=str(snapshot), files=files)
        receipt.write_text(json.dumps(info), encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_snapshot(receipt)
        info["offline_audited"] = True
        receipt.write_text(json.dumps(info), encoding="utf-8")
        self.assertEqual(verify_snapshot(receipt), snapshot)
        (snapshot / "checkpoint.pt").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            verify_snapshot(receipt)
