"""Auftragsmodell, Zustände, Ablage, Folgeaufträge."""
import json
import unittest

from hilfe import FUGUE, OMEN, TIDY1, TIDY2, Fall

from sirens.contracts import Ablehnung, safe_audio_path
from sirens.nachlauf import neu
from sirens.workflow import STATUS, lage


class Wunsch(Fall):
    def abschicken(self, **wunsch):
        order = self.nutzer.create_draft(wunsch)
        return self.nutzer.submit(order["id"], {"revision": order["revision"]})

    def test_weg1_eine_und_mehrere_referenzen(self):
        eins = self.abschicken(weg="referenz", artist_slug="cco", referenzen=[{"pfad": TIDY1}])
        ref = eins["wunsch"]["referenzen"][0]
        self.assertEqual((ref["artist_slug"], ref["release_slug"], ref["titel"], ref["version"], ref["gewicht"]),
                         ("cco", "lab-notes", "Too Tidy", 1, "normal"))
        self.assertEqual(eins["wunsch"]["bezug"], "im_stil")
        self.assertEqual(eins["status"], "offen")
        mehrere = self.abschicken(weg="referenz", artist_slug="cco", bezug="fortsetzung", referenzen=[
            {"pfad": TIDY1, "gewicht": "stark", "uebernehmen": "nur den Bass"}, {"pfad": OMEN}, {"pfad": TIDY1}])
        self.assertEqual([r["pfad"] for r in mehrere["wunsch"]["referenzen"]], [TIDY1, OMEN])
        self.assertEqual(mehrere["id"][-3:], "002")

    def test_weg2_song_album_und_bestehendes_album(self):
        album = self.abschicken(weg="beschreibung", umfang="album", track_count=8, artist_slug="cco",
                                wunsch="Funk, lustig", track_wuensche=[{"nr": 2, "text": "ein Instrumental"}],
                                optionen={"planfreigabe": "an", "zweitgutachten": "aus"})
        self.assertEqual(album["wunsch"]["track_count"], 8)
        self.assertEqual(album["wunsch"]["optionen"]["zweitgutachten"], "aus")
        schnell = self.entwurf(optionen={"tempo": "schnell", "planfreigabe": "an", "zweitgutachten": "an"})
        self.assertEqual(schnell["wunsch"]["optionen"]["planfreigabe"], "aus")
        self.assertEqual(schnell["wunsch"]["optionen"]["zweitgutachten"], "aus")
        self.assertEqual(album["wunsch"]["optionen"]["provider"], "suno")
        offen = self.abschicken(weg="beschreibung", umfang="album", artist_slug="cco", wunsch="x")
        self.assertIsNone(offen["wunsch"]["track_count"])
        song = self.abschicken(weg="beschreibung", artist_slug="cco", wunsch="x", ziel_release_slug="lab-notes",
                               track_count=5, track_wuensche=[{"nr": 1, "text": "egal"}])
        self.assertEqual((song["wunsch"]["ziel_release_slug"], song["wunsch"]["track_count"],
                          song["wunsch"]["track_wuensche"]), ("lab-notes", None, []))

    def test_ablehnungen_ohne_aenderung(self):
        unvollstaendig = [self.nutzer.create_draft({"weg": "referenz", "artist_slug": "cco"}),
                          self.nutzer.create_draft({"weg": "beschreibung", "artist_slug": "cco"})]
        vorher = self.ablage()
        for order, feld in zip(unvollstaendig, ("referenzen", "wunsch")):
            with self.assertRaises(Ablehnung) as ctx:
                self.nutzer.submit(order["id"], {"revision": order["revision"]})
            self.assertEqual(ctx.exception.feld, feld)
        schlecht = [{"geheim": 1}, {"plan": {}}, {"tracks_stand": []}, {"ergebnis": {}}, {"weg": "anders"},
                    {"umfang": "album", "track_count": 21}, {"optionen": {"provider": "udio"}},
                    {"optionen": {"neu": 1}}, {"referenzen": [{"pfad": TIDY1, "gewicht": "riesig"}]},
                    {"referenzen": [{"pfad": "cco/lab-notes/fehlt - Version 1.mp3"}]},
                    {"referenzen": [{"pfad": "cco/lab-notes/cover.png"}]},
                    {"referenzen": [{"pfad": f"cco/x - Version {i}.mp3"} for i in range(13)]}]
        for data in schlecht:
            with self.assertRaises(Ablehnung, msg=data):
                self.nutzer.create_draft(data)
        self.assertEqual(self.ablage(), vorher)

    def test_pfade(self):
        for pfad in ("../musik/" + TIDY1, "cco/../../x.mp3", "/etc/x.mp3", "C:/x.mp3", "C:\\x.mp3", "//server/f/x.mp3",
                     "\\\\server\\f\\x.mp3", "cco\\lab-notes\\x.mp3", "", None, 7):
            with self.assertRaises(Ablehnung, msg=pfad) as ctx:
                safe_audio_path(self.cfg.music_root, pfad)
            self.assertEqual(ctx.exception.code, "invalid_path")
        self.assertTrue(safe_audio_path(self.cfg.music_root, TIDY1).is_file())

    def test_wunsch_nach_abschicken_gesperrt_und_revision(self):
        order = self.entwurf()
        oid = order["id"]
        with self.assertRaises(Ablehnung) as ctx:
            self.nutzer.update_draft(oid, {"revision": order["revision"] + 5, "weg": "beschreibung"})
        self.assertEqual(ctx.exception.code, "revision_conflict")
        with self.assertRaises(Ablehnung):
            self.nutzer.update_draft(oid, {"weg": "beschreibung"})
        geaendert = self.nutzer.update_draft(oid, {"revision": 1, "weg": "beschreibung", "wunsch": "Funk",
                                                   "artist_slug": "cco"})
        self.assertEqual((geaendert["revision"], geaendert["wunsch"]["wunsch"]), (2, "Funk"))
        offen = self.nutzer.submit(oid, {"revision": 2})
        vorher = self.ablage()
        with self.assertRaises(Ablehnung) as ctx:
            self.nutzer.update_draft(oid, {"revision": offen["revision"], "wunsch": "anders"})
        self.assertEqual(ctx.exception.code, "not_editable")
        self.assertEqual(self.ablage(), vorher)
        self.assertEqual(json.loads(vorher[oid + ".json"])["wunsch"]["wunsch"], "Funk")
        self.assertEqual([n for n in vorher if not n.endswith(".json")], [])


class Zustaende(Fall):
    def test_lage_fuer_jeden_status(self):
        erwartet = {"entwurf": ("nutzer", 1), "offen": ("claude", 1), "in_arbeit": ("laeuft", 2),
                    "rueckfrage": ("nutzer", 2), "plan_wartet": ("nutzer", 3), "antwort_da": ("claude", 2),
                    "gesendet": ("laeuft", 4), "fertig": ("nutzer", 5), "abgeschlossen": ("niemand", 10),
                    "nachlauf": ("nutzer", 6),
                    "fehler": ("claude", 2), "abgebrochen": ("niemand", 0)}
        self.assertEqual(sorted(erwartet), STATUS)
        for status, (dran, station) in erwartet.items():
            stand = lage({"status": status, "plan": None, "tracks_stand": [], "bewertungen": [],
                          "nachlauf": neu("x.mp3")})
            self.assertEqual((stand["dran"], stand["station"]), (dran, station), status)
            self.assertTrue(stand["naechster_schritt"], status)
            self.assertEqual(stand["claude_auch_dran"], dran == "claude", status)
        mit_plan = lage({"status": "in_arbeit", "plan": {"tracks": []}, "tracks_stand": [], "bewertungen": []})
        self.assertEqual(mit_plan["station"], 3)
        weit = lage({"status": "in_arbeit", "plan": {}, "tracks_stand": [{"schritt": "paket"}], "bewertungen": []})
        self.assertEqual(weit["station"], 4)

    def test_claude_dran_wegen_offener_bewertungen(self):
        bew = [{"pfad": TIDY1, "score": 2, "uebernommen": False}]
        fertig = lage({"status": "fertig", "bewertungen": bew})
        self.assertEqual((fertig["dran"], fertig["claude_auch_dran"], fertig["offene_bewertungen"]), ("nutzer", True, 1))
        zu = lage({"status": "abgeschlossen", "bewertungen": bew})
        self.assertEqual((zu["dran"], zu["claude_auch_dran"]), ("claude", True))
        bew[0]["uebernommen"] = True
        self.assertEqual(lage({"status": "abgeschlossen", "bewertungen": bew})["dran"], "niemand")

    def test_unerlaubte_uebergaenge(self):
        order = self.entwurf()
        oid = order["id"]
        vorher = self.ablage()
        versuche = [lambda: self.claude.claim(oid), lambda: self.claude.ask(oid, "?"), lambda: self.claude.done(oid),
                    lambda: self.claude.sent(oid, "r"), lambda: self.claude.fail(oid, "x"),
                    lambda: self.claude.set_plan(oid, {"titel": "t"}),
                    lambda: self.claude.track(oid, 1, "text"),
                    lambda: self.nutzer.answer(oid, {"revision": 1, "text": "a"}),
                    lambda: self.nutzer.plan_decision(oid, {"revision": 1, "entscheidung": "freigeben"}),
                    lambda: self.nutzer.close(oid, {"revision": 1}),
                    lambda: self.nutzer.rate(oid, {"revision": 1, "pfad": TIDY1, "score": 1})]
        for versuch in versuche:
            with self.assertRaises(Ablehnung) as ctx:
                versuch()
            self.assertIn(ctx.exception.code, ("invalid_transition", "no_files"))
        self.assertEqual(self.ablage(), vorher)
        self.nutzer.cancel(oid, {"revision": 1})
        with self.assertRaises(Ablehnung):
            self.nutzer.submit(oid, {"revision": 2})
        fertig = self.fertiger_auftrag()
        with self.assertRaises(Ablehnung):
            self.nutzer.cancel(fertig["id"], {"revision": fertig["revision"]})

    def test_done_ohne_datei_und_fremde_datei(self):
        order = self.entwurf()
        oid = order["id"]
        self.nutzer.submit(oid, {"revision": 1})
        self.claude.claim(oid)
        self.claude.sent(oid, "r")
        vorher = self.ablage()
        with self.assertRaises(Ablehnung) as ctx:
            self.claude.done(oid)
        self.assertEqual(ctx.exception.code, "no_files")
        for datei in ("cco/lab-notes/fehlt.mp3", str(self.tmp / "fremd.mp3"), "../x.mp3"):
            with self.assertRaises(Ablehnung):
                self.claude.track(oid, 1, "fertig", files=[datei])
        self.assertEqual(self.ablage(), vorher)
        absolut = str(self.cfg.music_root / "cco" / "lab-notes" / "Too Tidy - Version 1.mp3")
        self.assertEqual(self.claude.track(oid, 1, "fertig", files=[absolut])["tracks_stand"][0]["dateien"], [TIDY1])


class Bewertung(Fall):
    def test_bewerten_favorit_und_grenzen(self):
        order = self.fertiger_auftrag()
        oid, rev = order["id"], order["revision"]
        vorher = self.ablage()
        for data in ({"pfad": TIDY1, "score": 3}, {"pfad": TIDY1, "score": -3}, {"pfad": TIDY1, "score": 1.5},
                     {"pfad": TIDY1, "score": True}, {"pfad": TIDY1}, {"pfad": FUGUE, "score": 1},
                     {"pfad": TIDY1, "score": 1, "uebernommen": True}, {"pfad": TIDY1, "score": 1, "favorit": "ja"}):
            with self.assertRaises(Ablehnung, msg=data):
                self.nutzer.rate(oid, {"revision": rev, **data})
        self.assertEqual(self.ablage(), vorher)
        order = self.nutzer.rate(oid, {"revision": rev, "pfad": TIDY1, "score": 2, "favorit": True})
        order = self.nutzer.rate(oid, {"revision": order["revision"], "pfad": TIDY2, "score": -1, "favorit": True,
                                       "kommentar": "zu brav"})
        bew = {b["pfad"]: b for b in order["bewertungen"]}
        self.assertEqual((bew[TIDY1]["favorit"], bew[TIDY2]["favorit"], bew[TIDY2]["kommentar"]),
                         (False, True, "zu brav"))
        self.claude.ratings_ack(oid, TIDY1, 431)
        self.claude.ratings_ack(oid, TIDY2)
        self.assertEqual(self.claude.ratings(oid), [])
        order = self.store.load(oid)
        gleich = self.nutzer.rate(oid, {"revision": order["revision"], "pfad": TIDY1, "score": 2})
        self.assertTrue(gleich["bewertungen"][0]["uebernommen"])
        neu = self.nutzer.rate(oid, {"revision": gleich["revision"], "pfad": TIDY1, "score": 1})
        self.assertFalse(neu["bewertungen"][0]["uebernommen"])
        self.assertNotIn("evaluation_id", neu["bewertungen"][0])
        self.assertEqual([b["pfad"] for b in self.claude.ratings(oid)], [TIDY1])


class Folgeauftrag(Fall):
    def test_alle_vorlagen(self):
        alt = self.fertiger_auftrag((TIDY1, TIDY2))
        oid = alt["id"]
        self.claude.track(oid, 2, "fertig", "Zwei", [FUGUE])
        ohne = self.nutzer.create_draft({"vorgaenger_id": oid, "vorlage": "mehr_davon"})
        self.assertEqual([r["pfad"] for r in ohne["wunsch"]["referenzen"]], [TIDY1, FUGUE])
        rev = self.store.load(oid)["revision"]
        rev = self.nutzer.rate(oid, {"revision": rev, "pfad": TIDY1, "score": 0})["revision"]
        rev = self.nutzer.rate(oid, {"revision": rev, "pfad": TIDY2, "score": 2})["revision"]
        rev = self.nutzer.rate(oid, {"revision": rev, "pfad": FUGUE, "score": 2})["revision"]
        for vorlage, bezug, gewicht in (("mehr_davon", "im_stil", "stark"), ("nochmal_anders", "neufassung", "normal"),
                                        ("fortsetzung", "fortsetzung", "normal")):
            neu = self.nutzer.create_draft({"vorgaenger_id": oid, "vorlage": vorlage})
            w = neu["wunsch"]
            self.assertEqual((neu["vorgaenger_id"], neu["status"], w["weg"], w["bezug"], w["artist_slug"]),
                             (oid, "entwurf", "referenz", bezug, "cco"), vorlage)
            self.assertEqual([(r["pfad"], r["gewicht"]) for r in w["referenzen"]],
                             [(TIDY2, gewicht), (FUGUE, gewicht)], vorlage)
        self.nutzer.rate(oid, {"revision": rev, "pfad": TIDY1, "score": 0, "favorit": True})
        favorit = self.nutzer.create_draft({"vorgaenger_id": oid, "vorlage": "fortsetzung"})
        self.assertEqual([r["pfad"] for r in favorit["wunsch"]["referenzen"]], [TIDY1])

    def test_nur_aus_fertigem_auftrag(self):
        entwurf = self.entwurf()
        vorher = self.ablage()
        for data in ({"vorgaenger_id": entwurf["id"], "vorlage": "mehr_davon"},
                     {"vorgaenger_id": "SA-20000101-001", "vorlage": "mehr_davon"},
                     {"vorgaenger_id": self.fertiger_auftrag()["id"], "vorlage": "irgendwie"}):
            vorher = self.ablage()
            with self.assertRaises(Ablehnung, msg=data):
                self.nutzer.create_draft(data)
        self.assertEqual(self.ablage(), vorher)


class Schema(Fall):
    def test_schema_passt_zum_code(self):
        from pathlib import Path
        from sirens.contracts import OPTIONEN, WUNSCH_FELDER
        from sirens.workflow import SCHRITTE
        schema = json.loads((Path(__file__).resolve().parent.parent / "auftrag.schema.json").read_text(encoding="utf-8"))
        eigenschaften = schema["properties"]
        order = self.fertiger_auftrag()
        order = self.nutzer.rate(order["id"], {"revision": order["revision"], "pfad": TIDY1, "score": 1})
        self.assertEqual(sorted(order), sorted(schema["required"]))
        self.assertEqual(sorted(eigenschaften["status"]["enum"]), STATUS)
        self.assertEqual(sorted(eigenschaften["wunsch"]["properties"]), sorted(WUNSCH_FELDER))
        self.assertEqual(sorted(eigenschaften["wunsch"]["properties"]["optionen"]["properties"]), sorted(OPTIONEN))
        self.assertEqual(eigenschaften["tracks_stand"]["items"]["properties"]["schritt"]["enum"], list(SCHRITTE))
        for teil in ("tracks_stand", "verlauf", "bewertungen"):
            erlaubt = set(eigenschaften[teil]["items"]["properties"])
            for eintrag in order[teil]:
                self.assertLessEqual(set(eintrag), erlaubt, teil)
                self.assertLessEqual(set(eigenschaften[teil]["items"]["required"]), set(eintrag), teil)
        self.assertEqual(sorted(order["ergebnis"]), sorted(eigenschaften["ergebnis"]["required"]))
        self.assertLessEqual(set(order["wunsch"]["referenzen"][0]),
                             set(eigenschaften["wunsch"]["properties"]["referenzen"]["items"]["properties"]))


if __name__ == "__main__":
    unittest.main()
