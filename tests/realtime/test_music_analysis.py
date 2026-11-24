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

    def test_disabled_model(self):
        import json
        from sirens.realtime.music_analysis import BeatThisLiveStub
        manifest_path = Path(__file__).resolve().parents[2]/"benchmarks"/"beatgrid"/"beat_this_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertFalse(manifest["available"])
        self.assertIsNone(manifest["worker_entrypoint"])
        adapter = BeatThisLiveStub()
        self.assertIsNone(adapter.probe())
        for call in (adapter.load, adapter.warmup, adapter.process, adapter.generate):
            with self.assertRaises(Ablehnung):
                call()
        adapter.cancel()
        adapter.unload()
        self.assertFalse(adapter.health()["available"])

    def test_reference_report(self):
        import json
        from unittest.mock import patch
        from benchmarks.beatgrid.measure import measure
        from benchmarks.result import read
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            audio = root/"source"
            audio.write_bytes(b"synthetische Quelle")
            local = root/"tracks.json"
            local.write_text(json.dumps({"tracks":[{
                "pfad":audio.name,"sha256":source_hash(audio),"genre":"Techno",
                "lizenz":"synthetisch","bpm":120,
                "beat_seconds":[.5,1,1.5,2],"downbeat_seconds":[0,2]}]}))
            target = root/"result.json"
            fake = {"confidence":.9,"grid":{"bpm":120,"beat0":0,"bar0":0,"confidence":.9}}
            with patch("benchmarks.beatgrid.measure.analyse_file",return_value=fake):
                data = measure(local,target)
            self.assertEqual(data,read(target))
            self.assertEqual(data["tracks"][0]["beat_seconds"]["max_ms"],0)
            self.assertEqual(data["tracks"][0]["downbeat_seconds"]["max_ms"],0)
            self.assertNotIn(str(root),target.read_text())
