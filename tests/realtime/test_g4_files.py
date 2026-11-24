import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.g4.await_file import wait


class FreshReport(unittest.TestCase):
    def test_existing_result_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                wait(path, 1)

    def test_wait_for_complete_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            def produce(_):
                path.write_text("{}", encoding="utf-8")
            with patch("benchmarks.g4.await_file.time.sleep", side_effect=produce):
                wait(path, 5)
            self.assertTrue(path.exists())

    def test_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(TimeoutError):
                wait(Path(tmp) / "missing.json", 0)
