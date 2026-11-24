"""CPU-Tests ohne Modell, Netz oder GPU."""
import unittest
from workers.stable_audio.adapter import Adapter, validate_job


def job(**changes):
    return dict(type="Fill", prompt="percussion", seed=42, strength=0.5,
                bars=4, duration=8, **{}) | changes


class StableAudioPadsTest(unittest.TestCase):
    def test_lifecycle_and_chunk(self):
        calls = []
        def infer(*args):
            calls.append(args)
            return b"\0" * 32
        adapter = Adapter(lambda: infer)
        adapter.load()
        with self.assertRaises(ValueError):
            adapter.generate(job())
        adapter.warmup()
        self.assertEqual(adapter.generate(job())["frames"], 4)
        self.assertEqual(calls[-1], ("Fill: percussion", 8, 42))
        self.assertEqual(adapter.chunk(1, 2), b"\0" * 16)
        with self.assertRaises(ValueError):
            adapter.chunk(3, 2)
        adapter.unload()
        with self.assertRaises(ValueError):
            adapter.chunk(0, 1)

    def test_validation(self):
        for changes in ({"seed": True}, {"bars": 3}, {"duration": 31},
                        {"strength": float("nan")}, {"prompt": ""}, {"path": "x"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_job(job(**changes))
