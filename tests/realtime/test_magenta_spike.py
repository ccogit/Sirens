"""Magenta-Spike-Regression ohne JAX, GPU oder Gewichte."""
import hashlib
import importlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

installer = importlib.import_module("benchmarks.spikes.magenta-realtime.install")
measure = importlib.import_module("benchmarks.spikes.magenta-realtime.messen")


class MagentaSpikeTests(unittest.TestCase):
    def test_manifest_and_no_download_without_flag(self):
        items = installer.manifest()
        self.assertEqual(len(items), 6)
        for item in items:
            self.assertTrue({"filename", "url", "size_bytes", "sha256", "license"} <= item.keys())
            self.assertEqual(len(item["sha256"]), 64)
            self.assertGreater(item["size_bytes"], 0)
        with patch.object(installer.urllib.request, "urlopen") as request, \
                patch.object(installer.subprocess, "run") as run:
            self.assertEqual(installer.main([]), 0)
            request.assert_not_called()
            run.assert_not_called()

    def test_download_rejects_corruption_and_reuses_valid(self):
        item = dict(filename="weights/test.safetensors", url="https://example.invalid",
                    size_bytes=3, sha256=hashlib.sha256(b"abc").hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for invalid in (b"bad", b"abcd", b"ab"):
                with patch.object(installer.urllib.request, "urlopen", return_value=io.BytesIO(invalid)):
                    with self.assertRaises(ValueError):
                        installer.obtain(item, root)
                self.assertFalse(list((root / "weights").iterdir()))
            with patch.object(installer.urllib.request, "urlopen", return_value=io.BytesIO(b"abc")) as request:
                path = installer.obtain(item, root)
                self.assertEqual(path.read_bytes(), b"abc")
                self.assertEqual(installer.obtain(item, root), path)
                request.assert_called_once()

    def test_dry_run(self):
        proc = subprocess.run([sys.executable, "-m", "benchmarks.spikes.magenta-realtime.messen",
                               "--dry-run"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Dry-Run OK", proc.stdout)

    def test_block_continues_state(self):
        class FakeModel:
            def generate(self, *, conditioning, frames, state):
                self.input = (conditioning, frames, state)
                return SimpleNamespace(sample_rate=48000,
                                       samples=SimpleNamespace(shape=(1920, 2))), "next"
        model = FakeModel()
        _, state = measure.one_block(model, {"style": [1]}, "previous")
        self.assertEqual(model.input, ({"style": [1]}, 1, "previous"))
        self.assertEqual(state, "next")
