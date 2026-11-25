"""AUFGABE-36: Getrennte Soak-Wertung ohne Audio-Hardware."""
import unittest

from benchmarks.g4.report import convert
from benchmarks.result import markdown, validate


class G4Underruns(unittest.TestCase):
    def setUp(self):
        self.machine = dict.fromkeys(("os", "python", "node", "ffmpeg", "gpus",
                                      "wsl", "disk", "git", "notes"))
        self.raw = dict(zeitpunkt="2026-11-25T12:00:00+00:00", requested_seconds=7200,
                        elapsed_seconds=7201, audio_seconds=7200, interruptions=0,
                        visibility_changes=0, epoch_changes=1, completed=True, error=None)

    def report(self, **counters):
        return validate(convert(dict(self.raw, **counters), "Performance", self.machine))

    def test_expected_only_passes_and_is_reported(self):
        data = self.report(unexpected_underruns=0, expected_underruns=128)
        self.assertEqual(data["soak_status"], "bestanden")
        self.assertEqual(data["gate"], "nicht_gemessen")
        self.assertEqual(data["elapsed_seconds"], 7201)
        self.assertEqual(data["messwerte"]["warm"]["underruns"], 0)
        self.assertEqual(data["messwerte"]["warm"]["unexpected_underruns"], 0)
        self.assertEqual(data["messwerte"]["warm"]["expected_underruns"], 128)
        self.assertIn("Erwartete Underruns: 128", markdown(data))

    def test_one_unexpected_fails_even_with_expected(self):
        data = self.report(unexpected_underruns=1, expected_underruns=128)
        self.assertEqual(data["soak_status"], "nicht bestanden")
        self.assertEqual(data["messwerte"]["warm"]["underruns"], 1)
        self.assertIn("Unerwartete Underruns: 1", markdown(data))

    def test_legacy_format(self):
        for count, status in [(0, "bestanden"), (1, "nicht bestanden")]:
            with self.subTest(count=count):
                data = self.report(underruns=count)
                self.assertEqual(data["soak_status"], status)
                self.assertEqual(data["messwerte"]["warm"]["underruns"], count)
                self.assertEqual(data["messwerte"]["warm"]["unexpected_underruns"], count)
                self.assertIsNone(data["messwerte"]["warm"]["expected_underruns"])
                self.assertIn("nicht getrennt erfasst (Altformat)", markdown(data))

    def test_explicit_unexpected_takes_precedence(self):
        data = self.report(underruns=128, unexpected_underruns=0, expected_underruns=128)
        self.assertEqual(data["soak_status"], "bestanden")
        self.assertEqual(data["messwerte"]["warm"]["underruns"], 0)

    def test_invalid_counters(self):
        for field in ("unexpected_underruns", "expected_underruns"):
            for value in (-1, True, 1.5, None):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    counters = dict(unexpected_underruns=0, expected_underruns=0)
                    counters[field] = value
                    self.report(**counters)

    def test_incomplete_soak_does_not_pass(self):
        for change in (dict(completed=False), dict(elapsed_seconds=10),
                       dict(audio_seconds=10), dict(error="Abbruch")):
            with self.subTest(change=change):
                raw = dict(self.raw, unexpected_underruns=0, expected_underruns=128)
                raw.update(change)
                data = convert(raw, "Performance", self.machine)
                self.assertEqual(data["soak_status"], "nicht bestanden")
                self.assertEqual(data["elapsed_seconds"], 0)
