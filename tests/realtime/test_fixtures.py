import tempfile
import unittest
import wave
from pathlib import Path

from benchmarks.fixtures import SIGNALS, generate, write_wav


class Fixtures(unittest.TestCase):
    def test_alle_signale_deterministisch(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.wav", Path(tmp) / "b.wav"
            for signal in SIGNALS:
                with self.subTest(signal=signal):
                    first = generate(signal, duration=0.25, channels=2)
                    second = generate(signal, duration=0.25, channels=2)
                    self.assertEqual(first, second)
                    write_wav(a, first)
                    write_wav(b, second)
                    self.assertEqual(a.read_bytes(), b.read_bytes())
                    self.assertTrue(all(-1 <= s <= 1 for s in first.samples))
                    with wave.open(str(a), "rb") as wav:
                        self.assertEqual((wav.getframerate(), wav.getnchannels(), wav.getnframes(), wav.getsampwidth()),
                                         (48000, 2, 12000, 3))

    def test_clicks_120_bpm(self):
        fixture = generate("click120", duration=4)
        beats = list(range(0, 192000, 24000))
        self.assertEqual(fixture.truth["beat_frames"], beats)
        self.assertEqual(fixture.truth["downbeat_frames"], [0, 96000])
        self.assertEqual([i for i, s in enumerate(fixture.samples) if s], beats)
        self.assertEqual([fixture.samples[i] for i in beats], [1, .5, .5, .5] * 2)

    def test_weitere_tempi(self):
        for bpm in (140, 150):
            fixture = generate(f"click{bpm}", duration=5, channels=2)
            beats = fixture.truth["beat_frames"]
            self.assertEqual(beats, [i for i in range(240000) if fixture.samples[i * 2]])
            for i, frame in enumerate(beats):
                self.assertLessEqual(abs(frame - i * 48000 * 60 / bpm), .5)
                self.assertEqual(fixture.samples[frame * 2], fixture.samples[frame * 2 + 1])

    def test_impuls_und_stille(self):
        fixture = generate("impuls", rate=8000, duration=.01, channels=2)
        self.assertEqual(sum(s != 0 for s in fixture.samples), 1)
        self.assertEqual(fixture.samples[0], 1)
        self.assertFalse(any(generate("stille", duration=.01).samples))

    def test_stereo_und_ungueltige_parameter(self):
        fixture = generate("stereo", rate=8000, duration=.01, channels=2)
        self.assertEqual(fixture.truth["frequencies_hz"], [440, 1000])
        self.assertNotEqual(fixture.samples[::2], fixture.samples[1::2])
        with self.assertRaises(ValueError):
            generate("stereo")
        with self.assertRaises(ValueError):
            generate("sinus440", rate=800)
