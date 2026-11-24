import unittest
from benchmarks.audio_core.format_result import convert
from benchmarks.result import validate


class AudioBenchmarkTests(unittest.TestCase):
    def test_format(self):
        raw = dict(elapsed_seconds=1800, completed=True, underruns=0,
                   skipped_blocks=0, interruptions=0, sample_rate=48000,
                   base_latency_ms=None, output_latency_ms=None,
                   zeitpunkt="2026-01-01T00:00:00+00:00")
        machine = dict.fromkeys(("os", "python", "node", "ffmpeg", "gpus", "wsl", "disk", "git", "notes"))
        out = validate(convert(raw, machine))
        self.assertIsNone(out["messwerte"]["warm"]["p95_ms"])
        self.assertEqual(out["messwerte"]["warm"]["underruns"], 0)
        self.assertEqual(out["gate"], "nicht_gemessen")
        self.assertEqual(validate(convert(raw, machine, [1, 2, 3]))["messwerte"]["warm"]["p95_ms"], 3)
        with self.assertRaises(ValueError):
            convert(dict(raw, underruns=-1), machine)
