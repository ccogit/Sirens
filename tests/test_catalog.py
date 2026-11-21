"""Referenzkatalog und Bewertungsanzeige."""
import json
import unittest

from hilfe import FUGUE, OMEN, TIDY1, TIDY2, Fall

from sirens.contracts import Ablehnung
from sirens.catalog import RICHTUNGSWOERTER, Katalog, bekannte_bewertungen, richtungswoerter


def pfade(baum):
    return [d["pfad"] for a in baum["artists"] for r in a["releases"] for s in r["songs"] for d in s["dateien"]]


class KatalogTest(Fall):
    def setUp(self):
        super().setUp()
        self.katalog = Katalog(self.cfg)
        self.katalog.scan()

    def test_aufbau(self):
        baum = self.katalog.baum({})
        self.assertEqual(baum["zustand"], "bereit")
        self.assertEqual(baum["kuenstler"], ["anna", "cco"])
        self.assertEqual(baum["anzahl_dateien"], 7)  # ohne flach liegende Datei, .asd, .png, .json
        self.assertNotIn("cco/flach.mp3", pfade(baum))
        cco = next(a for a in baum["artists"] if a["slug"] == "cco")
        self.assertEqual([r["slug"] for r in cco["releases"]], ["lab-notes", "nebelpuls"])
        songs = {s["titel"]: s["dateien"] for s in cco["releases"][0]["songs"]}
        self.assertEqual(sorted(songs), ["Fugue State", "Loser Name", "Too Tidy"])
        tidy = songs["Too Tidy"]  # mehrere Takes und eine Fassung im Unterordner bilden einen Song
        self.assertEqual([(d["version"], d["unterordner"], d["fassung"]) for d in tidy],
                         [(1, "", ""), (1, "mastered", "PreMix (eMastered)"), (2, "", "")])
        lose = songs["Loser Name"][0]  # tiefer verschachtelt, Muster passt nicht: nichts wird geraten
        self.assertEqual((lose["version"], lose["fassung"], lose["unterordner"]), (None, "", "alt/tief"))
        self.assertEqual(self.katalog.zahlen()["songs"], 5)

    def test_suche(self):
        self.assertEqual(pfade(self.katalog.baum({}, q="omen")), [OMEN])
        self.assertEqual(len(pfade(self.katalog.baum({}, q="LAB tidy"))), 3)
        self.assertEqual(pfade(self.katalog.baum({}, q="anna")), ["anna/erstes/Hallo - Version 1.mp3"])
        self.assertEqual(pfade(self.katalog.baum({}, q="gibtsnicht")), [])
        self.assertEqual(self.katalog.baum({}, q="gibtsnicht")["kuenstler"], ["anna", "cco"])

    def test_bewertungen_aus_beiden_quellen_und_min_score(self):
        self.assertEqual(bekannte_bewertungen(self.cfg, self.store), {})
        self.claude.catalog_ratings({TIDY1: {"score": 1, "label": "Too Tidy V1"}, OMEN: {"score": -2, "label": ""},
                                     FUGUE: {"score": 1, "label": "ok"}})
        order = self.fertiger_auftrag((TIDY1, TIDY2))
        rev = self.nutzer.rate(order["id"], {"revision": order["revision"], "pfad": TIDY1, "score": 2})["revision"]
        self.nutzer.rate(order["id"], {"revision": rev, "pfad": TIDY2, "score": 0})
        bew = bekannte_bewertungen(self.cfg, self.store)
        self.assertEqual((bew[TIDY1]["score"], bew[TIDY1]["quelle"]), (2, "auftrag"))  # die bessere gilt
        self.assertEqual((bew[FUGUE]["score"], bew[FUGUE]["quelle"], bew[FUGUE]["label"]), (1, "katalog", "ok"))
        self.assertEqual(bew[TIDY2]["score"], 0)
        baum = self.katalog.baum(bew)
        tidy1 = next(d for a in baum["artists"] for r in a["releases"] for s in r["songs"] for d in s["dateien"]
                     if d["pfad"] == TIDY1)
        self.assertEqual(tidy1["bewertung"]["score"], 2)
        self.assertEqual(sorted(pfade(self.katalog.baum(bew, min_score=1))), sorted([TIDY1, FUGUE]))
        self.assertEqual(pfade(self.katalog.baum(bew, min_score=2)), [TIDY1])
        self.assertEqual(len(pfade(self.katalog.baum(bew, min_score=-2))), 4)

    def test_achsen_des_songs_kommen_bis_zur_seite(self):
        achsen = {"energy": 7, "warmth": 3.5, "psychedelia": 9}
        self.claude.catalog_ratings({TIDY1: {"score": 1, "label": "gut", "achsen": achsen}})
        self.assertEqual(bekannte_bewertungen(self.cfg, self.store)[TIDY1]["achsen"], achsen)
        order = self.fertiger_auftrag()  # eine höhere Bewertung aus einem Auftrag verdrängt die Achsen nicht
        self.nutzer.rate(order["id"], {"revision": order["revision"], "pfad": TIDY1, "score": 2, "favorit": False, "kommentar": ""})
        self.assertEqual((bekannte_bewertungen(self.cfg, self.store)[TIDY1]["score"], bekannte_bewertungen(self.cfg, self.store)[TIDY1]["achsen"]), (2, achsen))
        for falsch in ({"tempo": 5}, {"energy": 11}, {"energy": "viel"}, [1, 2]):
            with self.assertRaises(Ablehnung):
                self.claude.catalog_ratings({TIDY1: {"score": 1, "label": "", "achsen": falsch}})

    def test_katalogbewertungen_ungueltig(self):
        from sirens.contracts import Ablehnung
        for data in ([1], {TIDY1: {"score": 5}}, {TIDY1: {"score": 1, "x": 1}}, {TIDY1: 2}):
            with self.assertRaises(Ablehnung):
                self.claude.catalog_ratings(data)
        self.assertFalse(self.cfg.catalog_ratings_file.exists())
        self.cfg.data_dir.mkdir(parents=True, exist_ok=True)
        self.cfg.catalog_ratings_file.write_text("kaputt", encoding="utf-8")
        self.assertEqual(bekannte_bewertungen(self.cfg, self.store), {})

    def test_hintergrundscan_und_aktualisieren(self):
        katalog = Katalog(self.cfg)
        self.assertEqual(katalog.baum({})["zustand"], "leer")
        katalog.scan_im_hintergrund()
        katalog.warten()
        self.assertEqual(katalog.zahlen()["dateien"], 7)
        neu = self.cfg.music_root / "anna" / "erstes" / "Hallo - Version 2.mp3"
        neu.write_bytes(b"")
        katalog.scan_im_hintergrund()
        katalog.warten()
        self.assertEqual(katalog.zahlen()["dateien"], 8)

    def test_richtungswoerter(self):
        self.assertEqual(richtungswoerter(self.cfg), RICHTUNGSWOERTER)
        self.cfg.data_dir.mkdir(parents=True, exist_ok=True)
        self.cfg.direction_words_file.write_text(json.dumps(["mehr Electro", " ", 5]), encoding="utf-8")
        self.assertEqual(richtungswoerter(self.cfg), ["mehr Electro"])


class OhneMusikordner(Fall):
    musik = False

    def test_fehlender_musikordner(self):
        katalog = Katalog(self.cfg)
        katalog.scan()
        baum = katalog.baum({})
        self.assertEqual((baum["zustand"], baum["error"], baum["artists"]), ("music_root_missing", "music_root_missing", []))
        self.assertIn("Musikordner", baum["meldung"])
        order = self.nutzer.create_draft({"weg": "beschreibung", "artist_slug": "cco", "wunsch": "Funk"})
        self.assertEqual(self.nutzer.submit(order["id"], {"revision": 1})["status"], "offen")


if __name__ == "__main__":
    unittest.main()
