import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sirens.production.instruments import WBWorker
from workers.production_instruments.render import local_bindings, resolve_bundle


class WindowsInstrumentTests(unittest.TestCase):
    def test_bundle_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "Surge XT.vst3"
            inner = bundle / "Contents" / "x86_64-win" / bundle.name
            inner.parent.mkdir(parents=True)
            inner.touch()
            self.assertEqual(resolve_bundle(bundle, windows=True), inner)
            self.assertEqual(resolve_bundle(bundle, windows=False), bundle)
            self.assertEqual(resolve_bundle(inner, windows=True), inner)
            inner.unlink()
            with self.assertRaisesRegex(ValueError, "Plugin bundle incomplete; set"):
                resolve_bundle(bundle, windows=True)
            with self.assertRaisesRegex(ValueError, "Plugin missing; set"):
                resolve_bundle(inner, windows=True)

    def test_external_plugin_and_preset_without_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "outside" / "Test.vst3"
            plugin.parent.mkdir()
            plugin.touch()
            preset = root / "patch.fxp"
            preset.write_bytes(b"fixture")
            binding = {"path": str(preset), "sha256": hashlib.sha256(b"fixture").hexdigest()}
            def unexpected(*args):
                self.fail("External bindings must not query WB roots")
            plugins = SimpleNamespace(plugin_path=unexpected)
            presets = SimpleNamespace(preset_file=unexpected)
            instrument = {"plugin": str(plugin) + "#Synth", "preset_file": binding}
            with local_bindings(instrument, plugins, presets, windows=True) as entry:
                self.assertEqual(plugins.plugin_path(str(plugin)), plugin)
                self.assertEqual(presets.preset_file(entry["plugin"], entry["preset"]), preset)
            self.assertIs(plugins.plugin_path, unexpected)
            self.assertIs(presets.preset_file, unexpected)
            self.assertNotIn("preset", instrument)
            preset.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Preset hash mismatch; update"):
                with local_bindings(instrument, plugins, presets, windows=True):
                    pass
            preset.unlink()
            with self.assertRaisesRegex(ValueError, "Preset missing; configure"):
                with local_bindings(instrument, plugins, presets, windows=True):
                    pass

    def test_legacy_wb_lookup_and_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "Test.vst3"
            plugin.touch()
            preset = root / "factory.fxp"
            preset.touch()
            plugins = SimpleNamespace(plugin_path=lambda ref: plugin)
            presets = SimpleNamespace(preset_file=lambda ref, ident: preset)
            inst = {"plugin": "vst3/Test.vst3", "preset": "factory"}
            with local_bindings(inst, plugins, presets, windows=False) as entry:
                self.assertEqual(plugins.plugin_path(entry["plugin"]), plugin)
                self.assertEqual(presets.preset_file(entry["plugin"], entry["preset"]), preset)
            preset.unlink()
            with self.assertRaisesRegex(ValueError, "Preset missing; configure"):
                with local_bindings(inst, plugins, presets, windows=False):
                    pass
            plugin.unlink()
            with self.assertRaisesRegex(ValueError, "Plugin missing or invalid; set"):
                with local_bindings(inst, plugins, presets, windows=False):
                    pass

    def test_worker_environment_is_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = os.environ.copy()
            with patch("sirens.production.integration.settings", return_value={"wb_data_dir": tmp}):
                worker = WBWorker(sys.executable, root, "fixture")
            with patch("sirens.production.instruments.subprocess.run",
                       return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
                worker.render({"track": {}}, root / "out.wav")
            kwargs = run.call_args.kwargs
            self.assertEqual(kwargs["env"]["WORKBENCH_DATA_DIR"], str(root.resolve()))
            self.assertEqual(kwargs["encoding"], "utf-8")
            self.assertEqual(json.loads(kwargs["input"])["amm_backend"], str(root.resolve()))
            self.assertEqual(os.environ.copy(), before)
            with patch("sirens.production.instruments.subprocess.run",
                       return_value=subprocess.CompletedProcess([], 1, "", "Preset missing; configure instrument.preset_file.")):
                with self.assertRaisesRegex(RuntimeError, "Preset missing; configure"):
                    worker.render({}, root / "out.wav")

    def test_host_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "Instrument host missing; set instrument_python"):
                WBWorker(Path(tmp) / "missing.exe", tmp, "fixture")

    def test_prepare_rejects_changed_preset_before_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "Test.vst3"
            plugin.touch()
            preset = root / "test.fxp"
            preset.write_bytes(b"test")
            worker = WBWorker(sys.executable, root, "fixture", wb_data_dir=root)
            request = {"patch": {"instrument": {"plugin": str(plugin),
                       "preset_file": {"path": str(preset), "sha256": hashlib.sha256(b"test").hexdigest()}}}}
            worker.prepare(request)
            self.assertEqual(request["wb_data_dir"], str(root.resolve()))
            preset.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Preset missing or hash mismatch; update"):
                worker.prepare(request)


if __name__ == "__main__":
    unittest.main()
