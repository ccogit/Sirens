"""Deterministic stage timing tests without workers or network."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from sirens.production.jobs import RunStore


class Clock:
    def __init__(self):
        self.value = 1000.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class StageTimingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cfg = SimpleNamespace(data_dir=Path(tmp.name))
        self.clock = Clock()
        self.store = RunStore(self.cfg, clock=self.clock)
        self.run, self.root = self.store.create()

    def test_progress_and_stage_changes(self):
        self.assertEqual(self.store.inspect(self.run)["stages"], [])
        self.clock.advance(10)
        first = self.store.status(self.run, "running", "assets", 0.2)
        self.assertIsNone(first["stages"][0]["finished"])
        self.assertIsNone(first["stages"][0]["seconds"])
        self.clock.advance(1.25)
        progress = self.store.status(self.run, "running", "assets", 0.3)
        self.assertEqual(first["timestamps"]["running"], progress["timestamps"]["running"])
        self.assertEqual(first["stages"], progress["stages"])
        self.clock.advance(0.75)
        second = self.store.status(self.run, "running", "stems", 0.4)
        self.assertEqual(second["stages"][0]["seconds"], 2.0)
        self.assertEqual(second["stages"][0]["finished"], second["stages"][1]["started"])
        self.clock.advance(3.5)
        final = self.store.status(self.run, "succeeded", "complete", 1)
        self.assertEqual([s["stage"] for s in final["stages"]], ["assets", "stems"])
        self.assertEqual([s["seconds"] for s in final["stages"]], [2.0, 3.5])
        self.assertEqual(final["total_seconds"], 5.5)
        self.assertEqual(final["stages"][-1]["finished"], final["timestamps"]["succeeded"])
        with (self.root / "status.json").open(encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), final)

    def test_cancel_and_failure_close_active_stage_not_requested_stage(self):
        for state in ("cancelled", "failed"):
            with self.subTest(state=state):
                run, _ = self.store.create()
                self.store.status(run, "running", "mix")
                self.clock.advance(2.25)
                final = self.store.status(run, state, "report")
                self.assertEqual(len(final["stages"]), 1)
                self.assertEqual(final["stages"][0]["stage"], "mix")
                self.assertEqual(final["stages"][0]["seconds"], 2.25)
                self.assertEqual(final["stages"][0]["finished"], final["timestamps"][state])
                self.assertEqual(final["total_seconds"], 2.25)

    def test_recovery_with_new_store_instance(self):
        self.store.status(self.run, "running", "assets")
        self.clock.advance(4)
        recovered = RunStore(self.cfg, clock=self.clock).recover(self.run)
        self.assertEqual(recovered["status"], "failed")
        self.assertEqual(recovered["stages"][0]["seconds"], 4.0)
        self.assertEqual(recovered["total_seconds"], 4.0)

    def test_legacy_status_and_queued_cancel(self):
        path = self.root / "status.json"
        legacy = self.store.inspect(self.run)
        del legacy["stages"]
        del legacy["total_seconds"]
        path.write_text(json.dumps(legacy), encoding="utf-8")
        self.assertEqual(self.store.inspect(self.run), legacy)
        self.clock.advance(3)
        final = self.store.status(self.run, "cancelled")
        self.assertEqual(final["stages"], [])
        self.assertEqual(final["total_seconds"], 0.0)

    def test_backwards_clock_does_not_produce_negative_duration(self):
        self.store.status(self.run, "running", "mix")
        self.clock.advance(-1)
        final = self.store.status(self.run, "failed", "mix")
        self.assertEqual(final["stages"][0]["seconds"], 0.0)
        self.assertEqual(final["total_seconds"], 0.0)
