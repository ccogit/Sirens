"""Der gemeinsame Katalog zeigt die migrierten Releases samt Stil, Fassungen und Single-Kollisionen."""
import contextlib
import io
import unittest

from hilfe import TIDY1, Fall
from sirens.catalog import Katalog, bekannte_bewertungen
from sirens.contracts import parse_pfad
from sirens.migrate_music import migrieren


class MusikablageTest(Fall):
    musik = False

    def test_umzug_erhaelt_inhalte_und_verweise(self):
        root = self.cfg.music_root
        for pfad in (TIDY1, "cco/lab-notes/Früher - Version 1.flac",
                     "cco/singles/afterglow/Afterglow.mp3", "anna/singles/afterglow/Afterglow.mp3",
                     "cco/lab-notes/mastered/eMastered_Too Tidy  Version 1_HD.wav",
                     "cco/lab-notes/stems/Too Tidy/drums.wav"):
            datei = root / pfad
            datei.parent.mkdir(parents=True, exist_ok=True)
            datei.write_text(pfad, encoding="utf-8")
        (root / "cco/lab-notes/Album-info.txt").write_text("Lab Notes\n01. Früher\n02. Too Tidy\n", encoding="utf-8")
        self.claude.catalog_ratings({TIDY1: {"score": 1, "label": "gut"}})
        with contextlib.redirect_stdout(io.StringIO()):
            migrieren(root, self.cfg.data_dir, ["cco", "anna"], anwenden=True)
        self.assertEqual({p.name for p in root.iterdir()}, {"Alben", "Singles", "_sirens"})
        neuer_pfad = "Alben/lab-notes/Too Tidy - Version 1.mp3"
        self.assertEqual((root / neuer_pfad).read_text(encoding="utf-8"), TIDY1)
        self.assertEqual(parse_pfad(neuer_pfad, root)["artist_slug"], "cco")
        bewertung = bekannte_bewertungen(self.cfg, self.store)
        self.assertEqual(bewertung[neuer_pfad]["score"], 1)
        katalog = Katalog(self.cfg)
        katalog.scan()
        releases = katalog.baum(bewertung)["releases"]
        self.assertEqual([r["pfad"] for r in releases],
                         ["Alben/lab-notes", "Singles/afterglow", "Singles/afterglow--cco"])
        self.assertEqual([s["titel"] for s in releases[0]["songs"]], ["Früher", "Too Tidy"])
        self.assertEqual(katalog.zahlen()["dateien"], 5)
        self.assertEqual(len(releases[0]["songs"][1]["dateien"]), 2)
        self.assertEqual([r["stilreferenz"] for r in releases], ["cco", "anna", "cco"])
