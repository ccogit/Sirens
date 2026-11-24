"""Statische Sicherheitsregression für die Modell-Spikes."""
import ast
from pathlib import Path
import unittest

SPIKES = Path(__file__).resolve().parents[2] / "benchmarks" / "spikes"


class SpikeWeightSafetyTests(unittest.TestCase):
    def test_no_explicit_unsafe_weight_load(self):
        scripts = sorted(SPIKES.glob("*/messen.py"))
        self.assertTrue(scripts)
        for path in scripts:
            with self.subTest(path=path.name, candidate=path.parent.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        self.assertFalse(
                            isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "pickle"
                            and node.func.attr in ("load", "loads")
                        )
                        for keyword in node.keywords:
                            if keyword.arg == "weights_only":
                                self.assertNotEqual(
                                    getattr(keyword.value, "value", None), False
                                )

    def test_roformer_manifest_and_download(self):
        import hashlib
        import importlib
        import io
        import json
        import tempfile
        from unittest.mock import patch

        installer = importlib.import_module("benchmarks.spikes.roformer-drumsep.install")
        manifest = json.loads((SPIKES / "roformer-drumsep" / "weights.json").read_text(encoding="utf-8"))
        for item in manifest["models"]:
            self.assertTrue({"url", "filename", "size_bytes", "sha256", "license"} <= item.keys())
        sample = dict(approved=True, filename="test.ckpt", size_bytes=3,
                      sha256=hashlib.sha256(b"abc").hexdigest(), url="https://example.invalid")
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with patch.object(installer.urllib.request, "urlopen", return_value=io.BytesIO(b"bad")):
                with self.assertRaises(ValueError):
                    installer.obtain_weight(sample, directory)
            self.assertFalse(list(directory.iterdir()))
            with patch.object(installer.urllib.request, "urlopen", return_value=io.BytesIO(b"abc")) as request:
                path = installer.obtain_weight(sample, directory)
                self.assertEqual(path.read_bytes(), b"abc")
                self.assertEqual(installer.obtain_weight(sample, directory), path)
                self.assertEqual(request.call_count, 1)
            with patch.object(installer.urllib.request, "urlopen") as request:
                with self.assertRaises(ValueError):
                    installer.obtain_weight(manifest["models"][1], directory)
                request.assert_not_called()
                self.assertEqual(installer.main([]), 0)
                request.assert_not_called()
