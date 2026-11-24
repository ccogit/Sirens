import unittest
from benchmarks.dsp.report import build
from benchmarks import result


class DspReportTest(unittest.TestCase):
    def test_node_format(self):
        machine = dict.fromkeys(("os", "python", "node", "ffmpeg", "gpus", "wsl", "disk", "git", "notes"))
        phase = {"p50_ms": 1, "p95_ms": 2, "p99_ms": 3, "rtf": .4}
        data = dict(backend="cpu", profile="fast", stems=2, frames=128, rate=48000,
                    latency_frames=896, kalt=phase, warm=phase)
        report = build(data, machine)
        self.assertEqual(report["gate"], "nicht_gemessen")
        self.assertIsNone(report["messwerte"]["warm"]["underruns"])
        self.assertEqual(result.validate(report), report)
