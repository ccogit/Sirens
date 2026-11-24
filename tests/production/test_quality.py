import tempfile
import unittest
import wave
from pathlib import Path

from sirens.production import quality


class QualityTests(unittest.TestCase):
    def test_pcm_peak_and_length(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mock.wav"
            with wave.open(str(path), "wb") as stream:
                stream.setparams((1, 3, 48000, 0, "NONE", ""))
                stream.writeframes(b"\x00\x00\x00\xff\xff\x7f")
            report = quality.measure_wav(path, 2)
            self.assertEqual(report["clipped_samples"], 1)
            self.assertEqual(report["frames"], 2)
            self.assertIsNone(report["true_peak_dbtp"])
            with self.assertRaises(ValueError):
                quality.measure_wav(path, 3)

    def test_worker_reuse_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                quality.mastering_analyzer(directory, directory)

    def test_blind_lock_and_reveal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mapping.json"
            public = quality.allocate_pair(path, "pair", "local", "reference", "seed",
                                           brief_id="brief", repetition=1,
                                           candidate_lufs=-12, reference_lufs=-14)
            self.assertEqual(set(public), {"pair_id", "labels"})
            mapping = quality._json(path)
            label = next(k for k, v in mapping["assignment"].items() if v["kind"] == "candidate")
            vote = dict(pair_id="pair", preference=label, music=4, production=5, locked=True)
            result = quality.reveal_pair(mapping, vote, {"A": -14, "B": -14.2})
            self.assertEqual(result["preference"], "candidate")
            with self.assertRaises(ValueError):
                quality.reveal_pair(mapping, vote, {"A": -14, "B": -13})
            with self.assertRaises(ValueError):
                quality.reveal_pair(mapping, dict(vote, locked=False), {"A": -14, "B": -14})
            with self.assertRaises(FileExistsError):
                quality.allocate_pair(path, "pair", "local", "reference", "seed",
                                      brief_id="brief", repetition=1,
                                      candidate_lufs=-12, reference_lufs=-14)

    def test_b2_threshold_not_release(self):
        rows = [dict(pair_id=f"{b}-{c}-{r}", brief_id=str(b), candidate_id=str(c),
                     repetition=r, preference="tie", music=4, production=4)
                for b in range(3) for c in range(2) for r in range(2)]
        self.assertTrue(quality.summarize_b2(rows)["threshold_met"])
        self.assertFalse(quality.summarize_b2(rows)["release"])
        self.assertFalse(quality.summarize_b2(rows[:-1])["threshold_met"])

    def test_missing_run_never_released(self):
        with tempfile.TemporaryDirectory() as directory:
            report = quality.inspect_run(directory)
            self.assertTrue(report["technical"]["errors"])
            self.assertEqual(report["gates"]["G2"]["status"], "failed")
            self.assertIsNone(report["music"]["score"])
