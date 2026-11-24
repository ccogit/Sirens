import unittest

from benchmarks.g4.report import convert
from benchmarks.result import validate


class SoakReport(unittest.TestCase):
    def test_duration_and_unmeasured_gate(self):
        machine = dict.fromkeys(("os", "python", "node", "ffmpeg", "gpus", "wsl", "disk", "git", "notes"))
        raw = dict(zeitpunkt="2026-11-24T12:00:00+00:00", requested_seconds=7200,
                   elapsed_seconds=7201, audio_seconds=7200, underruns=0, interruptions=0,
                   visibility_changes=0, epoch_changes=0, completed=True, error=None)
        data = validate(convert(raw, "Performance", machine))
        self.assertEqual(data["elapsed_seconds"], 7201)
        self.assertEqual(data["gate"], "nicht_gemessen")
        self.assertEqual(convert(dict(raw, audio_seconds=100), "Performance", machine)["elapsed_seconds"], 0)
        with self.assertRaises(ValueError):
            convert(dict(raw, underruns=-1), "Performance", machine)
