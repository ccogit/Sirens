import tempfile
import wave
import unittest
from pathlib import Path

from sirens.production import references as ref
from sirens.config import Config


class AmmExportTests(unittest.TestCase):
    def test_projection_and_inventory(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        cfg = Config(root / "music", root / "data")
        cfg.orders_dir.mkdir(parents=True)
        folder = cfg.music_root / "electro/funk"
        folder.mkdir(parents=True)
        a = "electro/funk/Alpha - Version 1.wav"
        b = "electro/funk/Alpha - Version 2.wav"
        for relative, value in ((a, 1), (b, 2)):
            with wave.open(str(cfg.music_root / relative), "wb") as wav:
                wav.setparams((1, 2, 8000, 0, "NONE", ""))
                wav.writeframes(bytes((value, 0)) * 800)
        evaluation = {"id": 7, "outcome_score": 2, "comment": "fixture"}
        common = {"song_id": 42, "package_created_at": "2026-01-01T00:00:00Z",
                  "package_id": 1, "style_prompt": "old", "song_evaluations": [evaluation]}
        newest = dict(common, package_id=2, style_prompt="new")
        rows = [dict(common, local_file_path=a),
                dict(newest, local_file_path=".\\generated-music\\" + a.replace("/", "\\")),
                dict(common, local_file_path=b),
                dict(common, local_file_path="electro/funk/Missing.wav"),
                dict(common, local_file_path="../outside.wav")]
        projection = ref.amm_export(rows, cfg.music_root)
        songs = projection["songs"]
        self.assertEqual(len(songs), 2)
        self.assertEqual({s["version"]: s["style_prompt"] for s in songs}, {1: "new", 2: "old"})
        self.assertEqual(songs[0]["song_evaluations"], songs[1]["song_evaluations"])
        self.assertEqual(songs[0]["song_evaluations"][0]["scope"], "song")
        tracks, coverage = ref.collect(cfg, amm_export=projection)
        self.assertEqual(coverage["raw_ratings"], 1)
        self.assertEqual(coverage["comments"], 1)
        self.assertEqual(coverage["with_prompts"], 2)
        self.assertTrue(all(t["rating"] == 2 for t in tracks))
