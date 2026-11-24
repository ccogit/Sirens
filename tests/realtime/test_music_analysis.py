import math
import random
import tempfile
import unittest
from pathlib import Path

from benchmarks.fixtures import generate
from sirens.contracts import Ablehnung
from sirens.realtime.music_analysis import (
    analyse_pcm, chroma_key, CorrectionStore, notes_to_frames, source_hash)
from sirens.realtime.schemas import validate


class MusicAnalysis(unittest.TestCase):
    def test_click_truth(self):
        for bpm in (120, 140, 150):
            with self.subTest(bpm=bpm):
                fixture = generate(f"click{bpm}", rate=4000, duration=24)
                result = analyse_pcm(fixture.samples)
                grid = validate("beatgrid", result["grid"])
                self.assertGreaterEqual(grid["confidence"], .5)
                self.assertAlmostEqual(grid["bpm"], bpm, delta=.2)
                period = 60*48000/grid["bpm"]
                for key, truth, step in (("beat0","beat_frames",period),
                                         ("bar0","downbeat_frames",4*period)):
                    for f in fixture.truth[truth]:
                        if f < 8000:
                            continue
                        actual = grid[key]+round((f*12-grid[key])/step)*step
                        self.assertLessEqual(abs(actual-f*12), 960)

    def test_silence_noise(self):
        rng = random.Random(42)
        for samples in ([0.]*40000, [rng.uniform(-.2,.2) for _ in range(40000)]):
            result = analyse_pcm(samples)
            self.assertIsNone(result["grid"])
            self.assertLess(result["confidence"], .5)
            self.assertEqual(result["key"], "unsicher")

    def test_chroma(self):
        # Betonter Grundton mit Terz und Quinte.
        samples = [sum(a*math.sin(math.tau*f*i/4000)
                       for a,f in ((.5,261.626),(.25,329.628),(.2,391.995)))
                   for i in range(8000)]
        key, confidence = chroma_key(samples, 4000)
        self.assertEqual(key, "C Dur")
        self.assertGreaterEqual(confidence,.5)

    def test_corrections(self):
        grid = {"bpm":120,"beat0":0,"bar0":0,"confidence":.8}
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/"source"
            source.write_bytes(b"synthetische Quelle")
            digest = source_hash(source)
            store = CorrectionStore(Path(folder)/"cache")
            self.assertIsNone(store.load(digest,48000))
            for action,value,expected in (
                ("half",None,{"bpm":60}),
                ("double",None,{"bpm":120}),
                ("bar",1,{"bar0":24000}),
                ("phase",480,{"beat0":480,"bar0":24480}),
                ("tap",[1000,20200,39400,58600],{"bpm":150,"beat0":1000,"bar0":1000})
            ):
                got = store.apply(digest,grid,48000,action,value)
                self.assertEqual(CorrectionStore(store.root).load(digest,48000),got)
                for key,v in expected.items():
                    self.assertEqual(got[key],v)
            self.assertEqual(store.load(digest,96000)["beat0"],2000)
            self.assertIsNone(store.load("a"*64,48000))
            with self.assertRaises(Ablehnung):
                store.apply(digest,grid,48000,"tap",[0,0,0])
            self.assertEqual(store.load(digest,48000),got)
            with self.assertRaises(Ablehnung):
                store.load("../test",48000)
            self.assertEqual(source.read_bytes(),b"synthetische Quelle")

    def test_midi_adapter(self):
        self.assertEqual(notes_to_frames([[.1,.25,60,.8]],48000),
                         [{"start_frame":4800,"end_frame":12000,"pitch":60,"amplitude":.8}])
        with self.assertRaises(Ablehnung):
            notes_to_frames([[0,1,128,.5]],48000)
