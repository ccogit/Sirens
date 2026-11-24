"""DEMON-Messpfad ohne GPU und Netz."""
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from benchmarks.spikes.demon import install


class DemonSpikeTests(unittest.TestCase):
    def test_dry_run(self):
        result = subprocess.run([sys.executable, "-m", "benchmarks.spikes.demon.messen", "--dry-run"],
                                capture_output=True, text=True, check=True)
        self.assertIn("Dry-Run OK", result.stdout)

    def test_manifest_and_guard(self):
        for item in install.manifest()["models"]:
            self.assertTrue({"url", "filename", "size_bytes", "sha256", "license"} <= item.keys())
            self.assertIn(install.manifest()["revision"], item["url"])
        with patch.object(install.urllib.request, "urlopen") as request:
            self.assertEqual(install.main([]), 0)
            request.assert_not_called()

    def test_hash_and_cleanup(self):
        item = dict(filename="model.safetensors", size_bytes=3,
                    sha256=hashlib.sha256(b"abc").hexdigest(), url="https://example.invalid")
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with patch.object(install.urllib.request, "urlopen", return_value=io.BytesIO(b"bad")):
                with self.assertRaises(ValueError):
                    install.obtain(item, directory)
            self.assertFalse(list(directory.iterdir()))
            with patch.object(install.urllib.request, "urlopen", return_value=io.BytesIO(b"abc")):
                self.assertEqual(install.obtain(item, directory)["size_bytes"], 3)
