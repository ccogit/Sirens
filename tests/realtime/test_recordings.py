import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from sirens.contracts import Ablehnung
from sirens.realtime.recordings import (Recording, RIFF_LIMIT, wav_header, repair,
                                         save_session, load_session, replay_parameters)


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "recordings"
        self.music = Path(self.temp.name) / "music"
        self.music.mkdir()

    def new(self, **kw):
        return Recording(self.root, self.music, "take", 48000, **kw)

    def test_fixture_segments(self):
        rec = self.new(segment_bytes=12)
        samples = [-0.9, 0.2, 0.0, -0.5, 0.999, -1.]
        rec.append(struct.pack("<6f", *samples), 0)
        parts = rec.stop()
        self.assertEqual(len(parts), 2)
        actual = []
        for path, frames in zip(parts, (2, 1)):
            with wave.open(str(path)) as w:
                self.assertEqual((w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()),
                                 (48000, 2, 3, frames))
                raw = w.readframes(frames)
                actual.extend(int.from_bytes(raw[i:i+3], "little", signed=True)/8388608
                              for i in range(0, len(raw), 3))
        for a, b in zip(actual, samples):
            self.assertLessEqual(abs(a-b), 1/8388608)
        header = wav_header(48000, RIFF_LIMIT)
        self.assertEqual(struct.unpack_from("<I", header, 4)[0], RIFF_LIMIT+36)
        with self.assertRaises(Ablehnung):
            wav_header(48000, RIFF_LIMIT+6)

    def test_repair_and_collision(self):
        a, b = self.new(), self.new()
        self.assertNotEqual(a.directory, b.directory)
        a.append(bytes(16), 0)
        a.file.write(b"x")
        a.file.close()
        path = repair(self.root, a.part.relative_to(self.root), self.music)
        with wave.open(str(path)) as w:
            self.assertEqual(w.getnframes(), 2)
        b.append(bytes(8), 0)
        self.assertNotEqual(b.stop()[0], path)

    def test_disk_full(self):
        a = self.new()
        a.append(bytes(16), 0)
        with patch.object(a, "_space", side_effect=OSError("Platte voll")):
            with self.assertRaisesRegex(Ablehnung, "Platte voll"):
                a.append(bytes(8), 2)
        with wave.open(str(a.stop()[0])) as w:
            self.assertEqual(w.getnframes(), 2)
        with self.assertRaises(Ablehnung):
            a.append(bytes(8), 2)

    def test_limit_and_path(self):
        a = self.new(max_bytes=6)
        a.append(bytes(8), 0)
        with self.assertRaises(Ablehnung):
            a.append(bytes(8), 1)
        self.assertEqual(len(a.stop()), 1)
        with self.assertRaises(Ablehnung):
            Recording(self.music / "take", self.music, "take", 48000)
        with self.assertRaises(Ablehnung):
            self.new().append(bytes(8), 1)
        with self.assertRaises(Ablehnung):
            repair(self.root, "../outside.wav.part", self.music)

    def test_session(self):
        value = {"version": 1, "sample_rate": 48000,
                 "sources": [{"asset_id": "a"*32, "sha256": "b"*64}],
                 "models": [{"name": "Mock", "version": "1"}], "presets": [],
                 "parameters": [{"name": "gain", "value": .25}],
                 "seeds": [{"name": "mock", "seed": 42}], "assets": ["c"*32],
                 "timeline": [{"frame": 10, "command": {"command": "set_param",
                     "epoch": 0, "seq": 0, "args": {"name": "gain", "value": .5}}}]}
        path = save_session(self.root, self.music, value)
        loaded = load_session(self.root, self.music, path.relative_to(self.root))
        self.assertEqual(loaded, value)
        self.assertEqual(replay_parameters(loaded, 0), {"gain": .25})
        self.assertEqual(replay_parameters(loaded, 10), {"gain": .5})
        value["seeds"][0]["seed"] = -1
        with self.assertRaises(Ablehnung):
            save_session(self.root, self.music, value)
        with self.assertRaises(Ablehnung):
            load_session(self.root, self.music, "../session.json")
