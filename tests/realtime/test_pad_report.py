import unittest

from benchmarks.pads.report import evaluate


class PadReportTest(unittest.TestCase):
    def test_observations(self):
        rows = [dict(job=i+1, target_frame=96000, scheduled_frame=96000,
                     observed_frame=96001, asset_ready_ms=500+i) for i in range(20)]
        rows[-1].update(scheduled_frame=192000, observed_frame=192000)
        counts, metrics = evaluate(rows)
        self.assertEqual(counts, dict(timely=19, shifted=1, dry=0, other=0, ratio=.95))
        self.assertEqual(metrics["p95_ms"], 518)
        rows[-2].update(observed_frame=None)
        self.assertEqual(evaluate(rows)[0]["other"], 1)
        with self.assertRaises(ValueError):
            evaluate(rows[:-1])
