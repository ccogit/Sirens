"""Runner timing integration with a fake backend and clock."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sirens.production import runner as runner_module
from sirens.production.contracts import read_manifest
from sirens.production.jobs import Cancelled


class RunnerStageTimingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.now = 1000.0
        self.backend = SimpleNamespace(
            assets=self.assets, stems=self.stems, mix=self.mix, report=self.report)
        self.runner = runner_module.Runner(
            SimpleNamespace(data_dir=Path(tmp.name)), self.backend,
            clock=lambda: self.now)
        # Isolate timing from unrelated audio/manifest contents. The actual
        # status and report validators and atomic JSON writers remain active.
        patches = patch.multiple(
            runner_module, validate_brief=Mock(), validate_plan=Mock(),
            validate_assets=Mock(), validate_stems=Mock(), validate_wav=Mock(),
            validate_mix_report=Mock(), expected_frames=Mock(return_value=1))
        patches.start()
        self.addCleanup(patches.stop)

    def assets(self, *args):
        self.now += 2.25
        return {"assets": []}

    def stems(self, *args):
        self.now += 3.5
        return {"stems": []}

    def mix(self, *args):
        self.now += 5
        return {}

    def report(self, *args):
        self.now += 1.25
        return dict(schema_version=1, technical={}, music={}, production={},
                    gates={}, missing=[], provenance={},
                    listening={"blind_pairs": [], "results": []})

    def render(self):
        return self.runner.render({}, {"seed": 7})

    def test_success_report_matches_terminal_status(self):
        status = self.render()
        self.assertEqual(status["status"], "succeeded")
        self.assertEqual([s["stage"] for s in status["stages"]],
                         ["prepare", "assets", "stems", "mix", "report"])
        self.assertEqual([s["seconds"] for s in status["stages"]],
                         [0, 2.25, 3.5, 5, 1.25])
        self.assertEqual(status["total_seconds"], 12)
        self.assertEqual(status["stages"][-1]["finished"],
                         status["timestamps"]["succeeded"])
        report = read_manifest(self.runner.store.get(status["run_id"]) / "report.json")
        self.assertEqual(report["stages"], status["stages"])
        self.assertEqual(report["total_seconds"], status["total_seconds"])

    def test_error_and_cancellation_inside_stage(self):
        for exc, expected in ((RuntimeError, "failed"), (Cancelled, "cancelled")):
            with self.subTest(state=expected):
                def stop(*args):
                    self.now += 4
                    raise exc("test")
                self.backend.stems = stop
                status = self.render()
                self.assertEqual(status["status"], expected)
                self.assertEqual([s["stage"] for s in status["stages"]],
                                 ["prepare", "assets", "stems"])
                self.assertEqual(status["stages"][-1]["seconds"], 4)
                self.assertEqual(status["stages"][-1]["finished"],
                                 status["timestamps"][expected])
                self.assertEqual(status["total_seconds"], 6.25)

    def test_cancel_between_stages(self):
        def request_cancel(brief, plan, root, cancel):
            self.now += 2
            self.runner.store.cancel(root.name)
            return {"assets": []}
        self.backend.assets = request_cancel
        status = self.render()
        self.assertEqual(status["status"], "cancelled")
        self.assertEqual(status["stage"], "assets")
        self.assertEqual([s["stage"] for s in status["stages"]],
                         ["prepare", "assets"])
        self.assertEqual(status["stages"][-1]["seconds"], 2)

    def test_technical_failure_report_contains_closed_stage(self):
        self.backend.require_technical_pass = True

        def invalid_report(*args):
            report = self.report(*args)
            report["technical"]["errors"] = ["test"]
            return report

        self.backend.report = invalid_report
        status = self.render()
        self.assertEqual(status["status"], "failed")
        report = read_manifest(self.runner.store.get(status["run_id"]) / "report.json")
        self.assertEqual(report["stages"], status["stages"])
        self.assertEqual(report["total_seconds"], status["total_seconds"])
        self.assertEqual(status["stages"][-1]["seconds"], 1.25)
