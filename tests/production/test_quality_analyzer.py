import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from sirens.config import Config
from sirens.production import quality
from sirens.production.__main__ import main


class AnalyzerTests(unittest.TestCase):
    def test_cli_configured_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cfg = Config(root / "music", root / "data")
            config = root / "config.json"
            config.write_text(json.dumps({"schema_version": 1, "analysis_python": "worker",
                                          "analysis_root": "engine"}), encoding="utf-8")
            analyzer = lambda path: {"lufs": -14, "true_peak_dbtp": -2,
                                     "measurement_method": "mock"}
            with patch.dict("os.environ", {"SIRENS_PRODUCTION_CONFIG": str(config)}), \
                 patch.object(quality, "mastering_analyzer", return_value=analyzer) as worker, \
                 patch.object(quality, "benchmark", return_value={"runs": []}) as benchmark, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["benchmark", "--manifest", "fixture.json"], cfg=cfg), 0)
            worker.assert_called_once_with("worker", "engine")
            benchmark.assert_called_once_with("fixture.json", analyzer=analyzer)

    def test_ffmpeg_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.wav"
            path.touch()
            stderr = "Summary:\n Integrated loudness:\n I: -14.2 LUFS\n LRA: 4.0 LU\n True peak:\n Peak: -1.8 dBFS\n"
            with patch.object(quality.shutil, "which", return_value="ffmpeg"), \
                 patch.object(quality.subprocess, "run", return_value=SimpleNamespace(stderr=stderr)) as run:
                measured = quality.configured_analyzer({})(path)
            self.assertEqual(measured["lufs"], -14.2)
            self.assertEqual(measured["true_peak_dbtp"], -1.8)
            self.assertEqual(measured["lra"], 4.0)
            self.assertIn("ebur128=peak=true", run.call_args.args[0])
            self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")

    def test_missing_analyzer_and_mock_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("mix.wav", "master.wav"):
                (root / name).touch()
            with patch.object(quality.shutil, "which", return_value=None):
                analyzer = quality.configured_analyzer({})
            self.assertIsNone(analyzer)
            def scan(*args):
                return {"clipped_samples": 0, "lufs": None, "true_peak_dbtp": None}
            with patch.object(quality, "measure_wav", side_effect=scan):
                missing = quality.inspect_run(root, analyzer)
                measured = quality.inspect_run(root, lambda path: {
                    "lufs": -14, "true_peak_dbtp": -2, "measurement_method": "mock"})
            for name in ("mix", "master"):
                self.assertIsNone(missing["technical"][name]["lufs"])
                self.assertIsNone(missing["technical"][name]["true_peak_dbtp"])
                self.assertIn("no analyzer", missing["technical"][name]["measurement_reason"])
                self.assertEqual(measured["technical"][name]["lufs"], -14)
                self.assertEqual(measured["technical"][name]["true_peak_dbtp"], -2)
