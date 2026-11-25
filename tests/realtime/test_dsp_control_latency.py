"""G3-Auswertung mit synthetischen Messdaten."""
import unittest
from benchmarks.dsp.report import build, breakdown


class DspControlReportTest(unittest.TestCase):
    def sample(self, total, base, output):
        return dict(total_ms=total, base_latency_ms=base, output_latency_ms=output,
                    rack_latency_ms=18.666, received_to_first_ms=1, first_to_90_ms=3)

    def test_paired_latency_and_g3_metric(self):
        data = dict(backend="cpu", profile="fast", stems=1,
                    control_ms=[80, 100, 90], control_samples=[
                        self.sample(80, 10, 50), self.sample(100, 40, 50),
                        self.sample(90, 10, 60)],
                    impulse={}, timeouts=0, render_ack_ms=[1, 2, 3])
        machine = dict.fromkeys(("os", "python", "node", "ffmpeg", "gpus", "wsl",
                                 "disk", "git", "notes"))
        report = build(data, machine)
        self.assertEqual(report["messwerte"]["warm"]["p95_ms"], 20)
        split = report["latency_breakdown"]
        self.assertEqual(split["total_ms"]["p95_ms"], 100)
        self.assertEqual(split["message_ms"]["p95_ms"], 16)
        self.assertEqual(split["samples_sirens"], 3)
        self.assertEqual(report["gate"], "nicht_gemessen")

    def test_missing_or_inconsistent_device_data(self):
        split = breakdown(dict(control_ms=[10, 20, 30], control_samples=[
            self.sample(10, None, 5), self.sample(20, 15, 10),
            self.sample(30, 10, 5)]))
        self.assertEqual(split["samples_sirens"], 1)
        self.assertEqual(split["sirens_ms"]["p95_ms"], 15)
        self.assertEqual(split["total_ms"]["p95_ms"], 30)
        legacy = breakdown(dict(control_ms=[80], output_latency_ms=50))
        self.assertIsNone(legacy["sirens_ms"]["p95_ms"])
        self.assertEqual(legacy["total_ms"]["p95_ms"], 80)

    def test_reject_invalid_samples(self):
        with self.assertRaises(ValueError):
            breakdown(dict(control_ms=[-1]))
        with self.assertRaises(ValueError):
            breakdown(dict(control_ms=[10], control_samples=[self.sample(11, 1, 1)]))
        with self.assertRaises(ValueError):
            breakdown(dict(control_ms=[10], control_samples=[self.sample(10, -1, 1)]))
