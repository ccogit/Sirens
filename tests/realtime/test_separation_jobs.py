import io
import tempfile
import time
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace

from sirens.config import Config
from sirens.contracts import Ablehnung
from sirens.realtime.stem_adapter import SeparationJobs, MODELS
from sirens.realtime.contracts import error


def wav(path):
    with wave.open(str(path), "wb") as f:
        f.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
        f.writeframes(bytes(1024))


class SeparationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        music = root / "music"
        music.mkdir()
        self.source = music / "song.wav"
        wav(self.source)
        self.cfg = Config(music, root / "data", rt_enabled=True)
        self.calls = []
        test = self

        class Worker:
            def __init__(self, registry, name, **kwargs):
                self.name = name
                self.file_progress = .5

            def start(self, **kwargs):
                test.calls.append(self.name)
                if self.name == "separation" and test.fail_roformer:
                    raise error("unavailable")

            def request_file_job(self, jid, source, out, params, timeout):
                target = out.with_name(jid + ".ready")
                target.mkdir(parents=True)
                model = "roformer" if self.name == "separation" else self.name
                files = [stem + ".wav" for stem in MODELS[model][1]]
                for name in files:
                    wav(target / name)
                return {"files": files, "vram_peak_bytes": 0}

            def close(self):
                pass

            def cancel(self):
                pass

        self.fail_roformer = False
        self.jobs = SeparationJobs(self.cfg, SimpleNamespace(root=root, env={}), None, Worker)
        self.addCleanup(self.jobs.close)

    def run_job(self, model="roformer"):
        job = self.jobs.start({"pfad": "song.wav", "model": model})
        thread = self.jobs.items[job["id"]]["_thread"]
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        result = self.jobs.job(job["id"])
        self.assertEqual(result["state"], "ready", result)
        return result

    def test_cache_assets_export(self):
        job = self.run_job()
        self.assertEqual(set(job["assets"]), {"original", "vocals", "instrumental"})
        self.assertEqual(self.calls, ["separation"])
        second = self.run_job()
        self.assertTrue(second["cache_hit"])
        self.assertEqual(self.calls, ["separation"])
        stem = second["assets"]["vocals"]
        self.assertEqual(self.jobs.asset(stem)["nframes"], 256)
        self.assertEqual(self.jobs.asset(stem, audio=True).name, "vocals.wav")
        original = self.source.read_bytes()
        exported = self.jobs.export(job["id"], io.BytesIO(original), len(original))
        self.assertEqual((self.cfg.realtime_dir / exported["file"]).read_bytes(), original)
        self.assertEqual(self.source.read_bytes(), original)
        with self.assertRaises(Ablehnung):
            self.jobs.export(job["id"], io.BytesIO(b"x"), 1)

    def test_fallback(self):
        self.fail_roformer = True
        job = self.run_job()
        self.assertEqual(job["fallback_from"], "roformer")
        self.assertEqual(job["model"], "htdemucs")
        self.assertEqual(self.calls, ["separation", "htdemucs"])
        self.assertEqual(set(job["assets"]), {"original", "vocals", "drums", "bass", "other"})

    def test_invalid_request(self):
        for body in ({"pfad": "../song.wav", "model": "roformer"},
                     {"pfad": "song.wav", "model": "drumsep"},
                     {"pfad": "song.wav", "model": "roformer", "out_dir": "/tmp"}):
            with self.assertRaises(Ablehnung):
                self.jobs.start(body)
        self.assertEqual(self.calls, [])
