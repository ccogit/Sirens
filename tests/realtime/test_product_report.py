import unittest
from benchmarks.integration.report import CHECKS, convert
from benchmarks.result import validate


class ProductReportTests(unittest.TestCase):
    def test_observations_do_not_grant_gate(self):
        machine = dict.fromkeys(("os", "python", "node", "ffmpeg", "gpus",
                                 "wsl", "disk", "git", "notes"))
        entries = {key: {"status": "bestanden", "note": "Test"} for key in CHECKS}
        result = validate(convert(machine, entries))
        self.assertEqual(result["gate"], "nicht_gemessen")
        self.assertTrue(all(value is None for value in result["messwerte"]["warm"].values()))
        del entries["panic"]
        with self.assertRaises(ValueError):
            convert(machine, entries)
