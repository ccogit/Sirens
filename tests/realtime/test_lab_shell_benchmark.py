"""WP05: Das manuelle Protokoll erfindet keine Messwerte."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("lab_shell_check", ROOT / "benchmarks/lab_shell/check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class LabShellBenchmark(unittest.TestCase):
    def test_result(self):
        machine = dict.fromkeys(("os", "python", "node", "ffmpeg", "gpus", "wsl", "disk", "git", "notes"))
        data = check.build_result(["offen"] * len(check.CHECKS), machine)
        from result import validate
        self.assertEqual(validate(data)["gate"], "nicht_gemessen")
        self.assertTrue(all(v is None for phase in data["messwerte"].values() for v in phase.values()))
        with self.assertRaises(ValueError):
            check.build_result(["ja"], machine)
