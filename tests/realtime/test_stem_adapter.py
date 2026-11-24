import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from sirens.contracts import Ablehnung
from sirens.realtime.stem_adapter import StemAdapter, MODELS


def wav(path, frames=16):
    with wave.open(str(path), "wb") as f:
        f.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
        f.writeframes(b"\\x00" * 4 * frames)


class StemAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.music = self.root / "music"
        self.music.mkdir()
        self.cache = self.root / "cache"
        wav(self.music / "song.wav")
        self.calls = []

    def runner(self, name):
        def run(source, output, params):
            self.calls.append(name)
            for stem in MODELS[name][1]:
                wav(output / (stem + ".wav"))
        return run

    def adapter(self, **runners):
        return StemAdapter(self.music, self.cache, runners)

    def test_cache_revision_params(self):
        adapter = self.adapter(roformer=self.runner("roformer"))
        first = adapter.separate("song.wav", "roformer")
        self.assertFalse(first["cache_hit"])
        self.assertTrue(adapter.separate("song.wav", "roformer")["cache_hit"])
        self.assertNotEqual(first["key"], adapter.separate("song.wav", "roformer", {"x": 1})["key"])
        rev, stems, enabled = MODELS["roformer"]
        with patch.dict(MODELS, roformer=(rev + "-new", stems, enabled)):
            self.assertNotEqual(first["key"], adapter.separate("song.wav", "roformer")["key"])
        self.assertEqual(len(self.calls), 3)

    def test_abort_and_fallback(self):
        def fail(source, output, params):
            wav(output / "vocals.wav")
            raise RuntimeError("abgebrochen")
        adapter = self.adapter(roformer=fail, htdemucs=self.runner("htdemucs"))
        with self.assertRaises(RuntimeError):
            adapter.separate("song.wav", "roformer", fallback=False)
        self.assertEqual(list(self.cache.iterdir()), [])
        result = adapter.separate("song.wav", "roformer")
        self.assertEqual(result["fallback_from"], "roformer")
        self.assertEqual(result["model"], "htdemucs")

    def test_bad_alignment(self):
        def short(source, output, params):
            wav(output / "vocals.wav", 15)
            wav(output / "instrumental.wav")
        adapter = self.adapter(roformer=short)
        with self.assertRaises(ValueError):
            adapter.separate("song.wav", "roformer", fallback=False)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_models(self):
        adapter = self.adapter(roformer=self.runner("roformer"))
        caps = {c["id"]: c for c in adapter.capabilities()}
        self.assertEqual(caps["roformer"]["stems"], ["vocals", "instrumental"])
        self.assertFalse(caps["drumsep"]["available"])
        self.assertEqual(caps["drumsep"]["stems"], [])
        with self.assertRaises(Ablehnung):
            adapter.separate("song.wav", "unknown")
