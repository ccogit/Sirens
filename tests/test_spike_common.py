import unittest
from benchmarks.spikes.common import percentile, rtf, summarize, make_result
from benchmarks.result import validate

class SpikeCommon(unittest.TestCase):
    def test_quantile(self):
        self.assertEqual(percentile([4, 1, 3, 2], 50), 2.5)
        self.assertAlmostEqual(percentile([0, 100], 95), 95)
        self.assertIsNone(percentile([], 99))
        self.assertEqual(rtf(2, 4), 0.5)
        with self.assertRaises(ValueError):
            rtf(1, 0)

    def test_format(self):
        machine = dict.fromkeys(("os", "python", "node", "ffmpeg", "gpus", "wsl", "disk", "git", "notes"))
        data = make_result("synthetischer Test", "unbekannt", machine,
                           summarize([(2, 4)]), summarize([(1, 4), (3, 4)]),
                           "unittest", ["Nur synthetische Testdaten"])
        self.assertEqual(validate(data)["gate"], "nicht_gemessen")
        self.assertAlmostEqual(data["messwerte"]["warm"]["rtf_p95"], 0.725)
