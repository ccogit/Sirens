import struct
import tempfile
import unittest
import wave
from pathlib import Path

from workers.stable_audio.adapter import Adapter
from workers.stable_audio.file_job import decode_params, render_file


class PadFileJobTest(unittest.TestCase):
    def test_render(self):
        calls = []
        def infer(*args):
            calls.append(args)
            return struct.pack("<ff", .5, -.5) * 4
        params = dict(pad_type=1, bars=1, bpm=120, key=1, seed=42, strength=.7, duration=2)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / "source.wav"
            source.write_bytes(b"unveraendert")
            out = root / ("a" * 32)
            out.mkdir()
            payload = dict(job_id=out.name, source=str(source), out_dir=str(out), params=params)
            adapter = Adapter(lambda: infer)
            with self.assertRaises(ValueError):
                render_file(adapter, payload)
            adapter.load()
            adapter.warmup()
            self.assertEqual(render_file(adapter, payload), {"files": ["pad.wav"]})
            self.assertEqual(calls[-1], ("Fill: electronic music, 120 BPM, C major", 2, 42))
            with wave.open(str(out / "pad.wav"), "rb") as wav:
                self.assertEqual((wav.getnchannels(), wav.getframerate(), wav.getnframes()), (2, 44100, 4))
                self.assertEqual(struct.unpack("<hh", wav.readframes(1)), (16384, -16384))
            self.assertEqual(source.read_bytes(), b"unveraendert")
            self.assertIsNone(adapter.clip)
            with self.assertRaises(ValueError):
                render_file(adapter, payload)
            adapter.unload()
            self.assertIsNone(adapter.model)

    def test_bad_params(self):
        good = dict(pad_type=1, bars=1, bpm=120, key=1, seed=42, strength=.7, duration=2)
        for changes in (dict(key=25), dict(pad_type=True), dict(bars=3), dict(seed=-1),
                        dict(bpm=float("nan")), dict(duration=31), dict(path="x")):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                decode_params(good | changes)
