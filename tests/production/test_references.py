"""Offline acceptance fixtures; generated files, no personal data."""
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from sirens.config import Config
from sirens.production import references as ref


def brief():
    return {"schema_version": 1, "title": "Test", "style": "electro funk",
            "negative_tags": [], "lyrics": None, "bpm": 126, "key": None,
            "target_seconds": 30, "seed": 1, "reference_ids": [], "vocal_mode": None}


class ReferencesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.cfg = Config(root / "music", root / "data")
        self.cfg.music_root.mkdir()
        self.cfg.data_dir.mkdir()
        self.cfg.orders_dir.mkdir()

    def audio(self, name, value):
        path = self.cfg.music_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            wav.writeframes(bytes((value, 0)) * 800)
        return name

    def ratings(self, rows):
        self.cfg.catalog_ratings_file.write_text(json.dumps(rows), encoding="utf-8")

    def test_inventory_conflicting_raw_and_catalog_maximum(self):
        a = self.audio("electro/funk/Alpha - Version 1.wav", 1)
        b = self.audio("electro/funk/Beta - Version 1.wav", 2)
        c = self.audio("electro/funk/Gamma - Version 1.wav", 3)
        self.ratings({a: {"score": 2, "achsen": {"energy": 8}}, c: {"score": 0}})
        order = {"id": "SA-20261124-001", "updated_at": "2026-11-24",
                 "bewertungen": [{"pfad": a, "score": -2, "favorit": True, "kommentar": "fixture"}]}
        (self.cfg.orders_dir / "SA-20261124-001.json").write_text(json.dumps(order), encoding="utf-8")
        tracks, coverage = ref.collect(self.cfg)
        tracks = {t["relative_path"]: t for t in tracks}
        self.assertEqual(tracks[a]["rating"], 2)
        self.assertEqual(tracks[a]["raw_ratings"][0]["score"], -2)
        self.assertEqual(tracks[a]["raw_comments"], ["fixture"])
        self.assertEqual(tracks[a]["axes"], {"energy": 8})
        self.assertTrue(tracks[a]["favorite"])
        self.assertIsNone(tracks[b]["rating"])
        self.assertIsNone(tracks[b]["style_text"])
        self.assertIsNone(tracks[b]["lyrics"])
        self.assertEqual(tracks[c]["rating"], 0)
        self.assertEqual(coverage["unrated"], 1)
        self.assertEqual(coverage["favorite_status"], "found")
        self.assertEqual(ref.build_references(list(tracks.values()), coverage, brief())["selected"], [])

    def test_master_duplicates_family_holdout(self):
        a = self.audio("electro/funk/Alpha - Version 1.wav", 1)
        b = self.audio("electro/funk/mastered/eMastered_Alpha Version 1.wav", 2)
        c = self.audio("electro/other/Copy - Version 2.wav", 1)
        extra = [self.audio(f"electro/funk/Track{i} - Version 1.wav", i+10) for i in range(8)]
        self.ratings({p: {"score": 2 if i % 2 == 0 else -1}
                      for i, p in enumerate(extra)} | {a: {"score": 2}, b: {"score": 2}})
        tracks, coverage = ref.collect(self.cfg)
        by_path = {t["relative_path"]: t for t in tracks}
        self.assertEqual(len({by_path[p]["song_family"] for p in (a, b, c)}), 1)
        result = ref.build_references(tracks, coverage, brief())
        held = {t["song_family"] for t in tracks if t["id"] in result["holdout"]}
        self.assertTrue(held)
        self.assertTrue(result["selected"])
        music = result["profile"]["music"]
        self.assertTrue(music["negative_examples"])
        used = set(result["selected"] + music["negative_examples"])
        for t in tracks:
            if t["song_family"] in held:
                self.assertIn(t["id"], result["holdout"])
                self.assertNotIn(t["id"], used)
        for pair in result["profile"]["production"]["original_master_pairs"]:
            self.assertNotIn(pair["master"], result["holdout"])
            self.assertNotIn(pair["original"], result["holdout"])
        self.assertEqual(len({t["song_family"] for t in tracks if t["id"] in used}), len(used))

    def test_read_only_amm_projection_and_lyrics(self):
        a = self.audio("electro/funk/Alpha - Version 1.wav", 1)
        folder = self.cfg.music_root / "electro/funk"
        (folder / "Alpha - Lyrics.txt").write_text("fixture lyrics", encoding="utf-8")
        row = {"artist_slug": "electro", "release_slug": "funk", "title": "Alpha",
               "version": 1, "style_prompt": "electro funk", "lyrics": None,
               "song_evaluations": [{"outcome_score": 1, "favorite": True}]}
        export = {"schema_version": 1, "songs": [row]}
        tracks, coverage = ref.collect(self.cfg, amm_export=export)
        t = tracks[0]
        self.assertEqual(t["relative_path"], a)
        self.assertEqual(t["style_text"], "electro funk")
        self.assertEqual(t["lyrics"], "fixture lyrics")
        self.assertEqual(t["rating"], 1)
        self.assertTrue(coverage["amm_available"])
        export["songs"].append(row.copy())
        tracks, coverage = ref.collect(self.cfg, amm_export=export)
        self.assertIsNone(tracks[0]["style_text"])
        self.assertEqual(coverage["amm_ambiguous"], 1)

    def test_measurement_hash_cache(self):
        self.audio("electro/funk/Alpha - Version 1.wav", 1)
        tracks, _ = ref.collect(self.cfg)
        cache = self.cfg.data_dir / "cache"
        measured = {"grid": {"bpm": 126, "confidence": 0.8},
                    "key": None, "key_confidence": None, "sections": [], "onsets": []}
        with patch("sirens.realtime.music_analysis.analyse_file", return_value=measured) as analyze:
            ref._measure(self.cfg, tracks[0], cache)
            ref._measure(self.cfg, tracks[0], cache)
            self.assertEqual(analyze.call_count, 1)
        self.assertEqual(tracks[0]["bpm_measured"], 126)
        self.assertEqual(tracks[0]["bpm_confidence"], 0.8)
        self.assertEqual(tracks[0]["features"]["method"], ref.METHOD)

    def test_missing_root(self):
        self.cfg.music_root.rmdir()
        tracks, coverage = ref.collect(self.cfg)
        self.assertEqual(tracks, [])
        self.assertEqual(coverage["catalog_status"], "music_root_missing")
        self.assertFalse(coverage["amm_available"])
        self.assertEqual(ref.build_references(tracks, coverage, brief())["selected"], [])


if __name__ == "__main__":
    unittest.main()
