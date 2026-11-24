import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.result import read
from benchmarks.system_suite import hashes, inventory, run, verify, worker_processes


class Registry:
    def capabilities(self):
        return [{"id": "new_model", "mock": False, "available": True, "mode": "streaming"},
                {"id": "disabled", "mock": False, "available": False, "mode": "offline"}]


class SystemSuite(unittest.TestCase):
    def test_dynamic_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "benchmarks/results/g1"
            folder.mkdir(parents=True)
            (folder / "new-model.md").write_text("**Gate: grün für den Modus `streaming`**",
                                                 encoding="utf-8")
            rows = {r["id"]: r for r in inventory(root, Registry())}
            self.assertTrue(rows["new_model"]["freigegeben"])
            self.assertFalse(rows["disabled"]["freigegeben"])

    def test_dry_run_and_original_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "music"
            music.mkdir()
            source = music / "test.wav"
            source.write_bytes(b"synthetic")
            out = root / "out"
            with patch("benchmarks.system_suite.inventory", return_value=[]):
                self.assertEqual(run(out, music, {}, True), 0)
            self.assertEqual(read(out / "suite.json")["gate"], "nicht_gemessen")
            original = hashes(music)
            source.write_bytes(b"changed")
            self.assertTrue(verify(original, hashes(music), set(), set()))
            with patch("benchmarks.system_suite.inventory", return_value=[]), \
                 patch("benchmarks.system_suite.hashes", side_effect=[original, hashes(music)]):
                self.assertEqual(run(root / "changed", music, {}, True), 1)

    def test_orphan_process(self):
        rows = [{"ProcessId": 1, "ParentProcessId": 0, "CreationDate": "a",
                 "CommandLine": "/repo/workers/mock/worker.py"},
                {"ProcessId": 2, "ParentProcessId": 1, "CreationDate": "b",
                 "CommandLine": "python"}]
        workers = worker_processes(rows, Path("/repo"))
        self.assertEqual(workers, {(1, "a"), (2, "b")})
        self.assertTrue(verify({}, {}, set(), workers))
        self.assertFalse(verify({}, {}, workers, workers))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("benchmarks.system_suite.inventory", return_value=[]), \
                 patch("benchmarks.system_suite.worker_processes", side_effect=[set(), workers]):
                self.assertEqual(run(root / "out", None, {}, False, snapshot=lambda: []), 1)
