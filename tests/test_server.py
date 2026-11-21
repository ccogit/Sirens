"""HTTP-API: vollständiger Lebenslauf über API und CLI, Sicherheit, Audio."""
import json
import unittest
from pathlib import Path

from hilfe import TIDY1, TIDY2, Fall, ServerFall

from sirens.config import Config
from sirens.contracts import Ablehnung
from sirens.server import make_server


class Lebenslauf(ServerFall):
    def post(self, oid, aktion, **body):
        _, order, _ = self.http("GET", f"/api/auftraege/{oid}")
        status, antwort, _ = self.http("POST", f"/api/auftraege/{oid}/{aktion}", {"revision": order["revision"], **body})
        self.assertEqual(status, 200, antwort)
        return antwort

    def lage(self, oid):
        order = self.http("GET", f"/api/auftraege/{oid}")[1]
        return order["status"], order["lage"]["dran"], order["lage"]["station"]

    def test_mit_rueckfrage_und_planfreigabe(self):
        status, order, _ = self.http("POST", "/api/auftraege", {
            "weg": "referenz", "umfang": "album", "track_count": 2, "artist_slug": "cco",
            "referenzen": [{"pfad": TIDY1}], "optionen": {"planfreigabe": "an"}})
        self.assertEqual((status, order["status"], order["lage"]["dran"]), (201, "entwurf", "nutzer"))
        oid = order["id"]
        status, order, _ = self.http("PUT", f"/api/auftraege/{oid}", {**order["wunsch"], "revision": 1,
                                                                    "wunsch": "treibender"})
        self.assertEqual((status, order["wunsch"]["wunsch"]), (200, "treibender"))
        self.post(oid, "abschicken")
        self.assertEqual(self.lage(oid), ("offen", "claude", 1))
        self.assertEqual([t["id"] for t in self.cli("todo")["todo"]], [oid])
        gezeigt = self.cli("show", oid)
        self.assertTrue(gezeigt["wunsch"]["referenzen"][0]["existiert"])
        self.assertTrue(Path(gezeigt["wunsch"]["referenzen"][0]["absolut"]).is_file())
        self.assertEqual(self.cli("claim", oid)["status"], "in_arbeit")
        self.assertEqual(self.lage(oid), ("in_arbeit", "laeuft", 2))
        self.cli("note", oid, "--text", "Referenz in der Datenbank gefunden.")
        self.cli("ask", oid, "--text", "Mit oder ohne Gesang?")
        self.assertEqual(self.lage(oid), ("rueckfrage", "nutzer", 2))
        liste = self.http("GET", "/api/auftraege?dran=nutzer")[1]["auftraege"]
        self.assertEqual((liste[0]["id"], liste[0]["frage"]), (oid, "Mit oder ohne Gesang?"))
        self.post(oid, "antwort", text="Mit Gesang.")
        self.assertEqual(self.lage(oid), ("antwort_da", "claude", 2))
        self.assertEqual(self.cli("todo")["todo"][0]["letzte_nutzernachricht"], "Mit Gesang.")
        self.cli("claim", oid)
        plan = self.tmp / "plan.json"
        plan.write_text(json.dumps({"titel": "Neue Notizen", "konzept": "Labor, aber treibender", "tracks": [
            {"nr": 1, "titel": "Eins", "idee": "Auftakt", "stil_kurz": "Electro-Funk"},
            {"nr": 2, "titel": "Zwei", "idee": "Schluss", "stil_kurz": "Acid"}]}), encoding="utf-8")
        self.cli("plan", oid, "--file", str(plan), "--wait")
        self.assertEqual(self.lage(oid), ("plan_wartet", "nutzer", 3))
        self.post(oid, "plan", entscheidung="aendern", text="Insgesamt lustiger", tracks=[{"nr": 2, "text": "kein Acid"}])
        todo = self.cli("todo")["todo"][0]
        self.assertEqual((todo["gruende"], todo["letzte_nutzernachricht"]),
                         (["Planänderung gewünscht"], "Insgesamt lustiger\nSong 2: kein Acid"))
        self.cli("claim", oid)
        plan.write_text(json.dumps({"tracks": [{"nr": 2, "stil_kurz": "Disco"}]}), encoding="utf-8")
        self.cli("plan", oid, "--file", str(plan), "--wait")
        self.post(oid, "plan", entscheidung="freigeben")
        self.assertEqual(self.cli("todo")["todo"][0]["gruende"], ["Plan freigegeben."])
        self.cli("claim", oid)
        plan.write_text(json.dumps({"tracks": [{"nr": 1, "text": "[Intro]\nLa la"}]}), encoding="utf-8")
        self.cli("plan", oid, "--file", str(plan))
        order = self.http("GET", f"/api/auftraege/{oid}")[1]
        self.assertEqual([(t["titel"], t["stil_kurz"], t["text"]) for t in order["plan"]["tracks"]],
                         [("Eins", "Electro-Funk", "[Intro]\nLa la"), ("Zwei", "Disco", "")])
        self.assertEqual((order["plan"]["titel"], order["lage"]["station"]), ("Neue Notizen", 3))
        self.cli("track", oid, "--nr", "1", "--schritt", "text")
        self.cli("track", oid, "--nr", "1", "--schritt", "paket")
        self.assertEqual(self.lage(oid), ("in_arbeit", "laeuft", 4))
        self.cli("track", oid, "--nr", "1", "--schritt", "geprueft")
        self.cli("sent", oid, "--release", "neue-notizen", "--song", "eins", "--song", "zwei", "--package", "41")
        self.assertEqual(self.lage(oid), ("gesendet", "laeuft", 4))
        self.assertEqual(self.cli("done", oid, ok=False)["error"], "no_files")
        stand = self.cli("track", oid, "--nr", "1", "--schritt", "fertig", "--file", TIDY1, "--file", TIDY2)
        self.assertEqual(stand["tracks_stand"][0], {"nr": 1, "titel": "Eins", "schritt": "fertig",
                                                    "dateien": [TIDY1, TIDY2]})
        self.cli("done", oid)
        self.assertEqual(self.lage(oid), ("fertig", "nutzer", 5))
        self.post(oid, "bewertung", pfad=TIDY2, score=2, favorit=True, kommentar="genau so")
        self.assertEqual(self.cli("ratings", oid)["bewertungen"][0]["pfad"], TIDY2)
        self.assertEqual(self.cli("todo")["todo"][0]["gruende"], ["1 Bewertung(en) übernehmen"])
        self.post(oid, "abschliessen")
        self.assertEqual(self.lage(oid), ("abgeschlossen", "claude", 10))
        self.cli("ratings-ack", oid, "--pfad", TIDY2, "--evaluation-id", "431")
        self.assertEqual(self.lage(oid), ("abgeschlossen", "niemand", 10))
        self.assertEqual(self.cli("todo")["todo"], [])
        order = self.http("GET", f"/api/auftraege/{oid}")[1]
        self.assertEqual(order["ergebnis"], {"release_slug": "neue-notizen", "song_slugs": ["eins", "zwei"],
                                             "package_ids": [41]})
        self.assertEqual(order["bewertungen"][0]["evaluation_id"], 431)
        self.assertEqual({e["art"] for e in order["verlauf"]},
                         {"status", "notiz", "rueckfrage", "antwort", "plan_aenderung"})
        status, folge, _ = self.http("POST", "/api/auftraege", {"vorgaenger_id": oid, "vorlage": "mehr_davon"})
        self.assertEqual((status, folge["vorgaenger_id"], folge["wunsch"]["referenzen"][0]["pfad"]), (201, oid, TIDY2))
        katalog = self.http("GET", "/api/catalog?min_score=2")[1]
        self.assertEqual(katalog["anzahl_dateien"], 1)

    def test_ohne_rueckfrage_und_planfreigabe(self):
        order = self.http("POST", "/api/auftraege", {"weg": "beschreibung", "artist_slug": "cco", "wunsch": "Funk"})[1]
        oid = order["id"]
        self.post(oid, "abschicken")
        self.cli("claim", oid)
        self.cli("track", oid, "--nr", "1", "--schritt", "gesendet", "--titel", "Funk")
        self.cli("sent", oid, "--release", "funk")
        self.cli("track", oid, "--nr", "1", "--schritt", "fertig", "--file", TIDY1)
        self.cli("done", oid)
        self.post(oid, "bewertung", pfad=TIDY1, score=-1)
        self.cli("ratings-ack", oid, "--pfad", TIDY1)
        self.post(oid, "abschliessen")
        self.assertEqual(self.lage(oid), ("abgeschlossen", "niemand", 10))
        self.assertEqual(self.cli("list", "--status", "abgeschlossen")["auftraege"][0]["id"], oid)
        self.assertEqual(self.cli("list", "--dran", "claude")["auftraege"], [])

    def test_fehler_und_abbruch(self):
        oid = self.http("POST", "/api/auftraege", {"weg": "beschreibung", "artist_slug": "cco", "wunsch": "x"})[1]["id"]
        self.post(oid, "abschicken")
        self.cli("claim", oid)
        self.cli("fail", oid, "--text", "Der Anbieter hat abgelehnt.")
        self.assertEqual(self.lage(oid)[:2], ("fehler", "claude"))
        self.cli("claim", oid)
        self.post(oid, "abbrechen")
        self.assertEqual(self.lage(oid), ("abgebrochen", "niemand", 0))
        self.assertEqual(self.cli("claim", oid, ok=False)["error"], "invalid_transition")
        self.assertEqual(self.cli("show", "SA-20000101-001", ok=False)["error"], "not_found")
        self.assertEqual(self.cli("unbekannt", ok=False)["error"], "usage")


class Dienst(ServerFall):
    def test_seite_health_und_einstellungen(self):
        status, seite, kopf = self.http("GET", "/", roh=True)
        self.assertEqual(status, 200)
        self.assertIn(b"Sirens", seite)
        self.assertIn("text/html", kopf["Content-Type"])
        self.assertEqual(self.http("GET", "/js/logic.js", roh=True)[0], 200)
        status, health, _ = self.http("GET", "/api/health")
        self.assertEqual((status, health["status"], health["auftraege"], health["music_root_vorhanden"]),
                         (200, "ok", 0, True))
        self.assertEqual((health["katalog"]["dateien"], health["katalog"]["songs"]), (7, 5))
        self.assertEqual(self.http("GET", "/api/einstellungen")[1]["satz"], "Bearbeite die Songaufträge")
        for pfad in ("/../sirens/server.py", "/%2e%2e/README.md", "/gibtsnicht.html", "/api/unbekannt"):
            self.assertEqual(self.http("GET", pfad, roh=True)[0], 404, pfad)

    def test_audio(self):
        from urllib.parse import quote
        url = "/api/audio?pfad=" + quote(TIDY1)
        status, inhalt, kopf = self.http("GET", url, roh=True)
        self.assertEqual((status, inhalt, kopf["Content-Type"], kopf["Accept-Ranges"]),
                         (200, b"0123456789", "audio/mpeg", "bytes"))
        for bereich, erwartet, content_range in (("bytes=2-5", b"2345", "bytes 2-5/10"), ("bytes=7-", b"789", "bytes 7-9/10"),
                                                 ("bytes=-3", b"789", "bytes 7-9/10"), ("bytes=8-99", b"89", "bytes 8-9/10")):
            status, inhalt, kopf = self.http("GET", url, headers={"Range": bereich}, roh=True)
            self.assertEqual((status, inhalt, kopf["Content-Range"]), (206, erwartet, content_range), bereich)
        for bereich in ("bytes=10-", "bytes=5-2", "bytes=-", "zeilen=1-2"):
            status, _, kopf = self.http("GET", url, headers={"Range": bereich}, roh=True)
            self.assertEqual((status, kopf["Content-Range"]), (416, "bytes */10"), bereich)
        for pfad, code in (("cco/lab-notes/cover.png", 400), ("stamm.json", 400), ("../daten/x.mp3", 400),
                           ("C:/x.mp3", 400), ("//server/x.mp3", 400), ("/etc/x.mp3", 400),
                           ("cco\\lab-notes\\Too Tidy - Version 1.mp3", 400), ("cco/lab-notes/fehlt.mp3", 404), ("", 400)):
            self.assertEqual(self.http("GET", "/api/audio?pfad=" + quote(pfad))[0], code, pfad)

    def test_beat_analyse_sicher_und_zwischengespeichert(self):
        from unittest.mock import patch
        from urllib.parse import quote
        route = "/api/beat?pfad=" + quote(TIDY1)
        with patch("sirens.beat.analysieren", return_value={"bpm": 120.0, "bar0": 0.0,
                                                            "cues_in": [], "cues_out": []}) as analyse:
            status, erste, _ = self.http("GET", route)
            zweiter = self.http("GET", route)[1]
            self.assertEqual((status, erste["bpm"], zweiter), (200, 120.0, erste))
            analyse.assert_called_once()
        self.assertEqual(self.http("GET", "/api/beat?pfad=../fremd.mp3")[0], 400)
        self.assertEqual(self.http("GET", "/api/beat?pfad=cco/fehlt.mp3")[0], 404)

    def test_schreibschutz_und_herkunft(self):
        gut = {"weg": "beschreibung", "artist_slug": "cco", "wunsch": "x"}
        fremd = self.http("POST", "/api/auftraege", gut, {"Origin": "http://boese.example"})
        self.assertEqual((fremd[0], fremd[1]["error"]), (403, "forbidden_origin"))
        self.assertEqual(self.http("POST", "/api/auftraege", gut, {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.http("GET", "/api/health", headers={"Host": "boese.example"})[0], 403)
        self.assertEqual(self.http("POST", "/api/auftraege", gut, {"Origin": self.basis})[0], 201)
        oid = self.http("GET", "/api/auftraege")[1]["auftraege"][0]["id"]
        vorher = self.ablage()
        for feld in ("plan", "tracks_stand", "ergebnis", "status", "bewertungen", "verlauf"):
            status, antwort, _ = self.http("PUT", f"/api/auftraege/{oid}", {**gut, "revision": 1, feld: []})
            self.assertEqual((status, antwort["error"], antwort["feld"]), (400, "unknown_field", feld))
            self.assertEqual(self.http("POST", "/api/auftraege", {**gut, feld: []})[0], 400)
        self.assertEqual(self.http("PUT", f"/api/auftraege/{oid}", {**gut, "revision": 9})[1]["error"], "revision_conflict")
        self.assertEqual(self.http("POST", f"/api/auftraege/{oid}/abschicken", {})[1]["error"], "required")
        self.assertEqual(self.http("POST", f"/api/auftraege/{oid}/claim", {"revision": 1})[0], 404)
        self.assertEqual(self.http("POST", f"/api/auftraege/{oid}/abschliessen", {"revision": 1})[0], 409)
        self.assertEqual(self.ablage(), vorher)
        fertig = self.fertiger_auftrag()
        status, antwort, _ = self.http("POST", f"/api/auftraege/{fertig['id']}/bewertung", {
            "revision": fertig["revision"], "pfad": TIDY1, "score": 2, "uebernommen": True})
        self.assertEqual((status, antwort["feld"]), (400, "uebernommen"))
        self.assertEqual(self.http("POST", "/api/catalog/refresh", {})[0], 202)

    def test_musikordner_bleibt_unberuehrt(self):
        vorher = sorted(p.relative_to(self.cfg.music_root).as_posix() for p in self.cfg.music_root.rglob("*"))
        self.fertiger_auftrag()
        self.http("GET", "/api/catalog")
        self.http("POST", "/api/catalog/refresh", {})
        self.server.app.katalog.warten()
        nachher = sorted(p.relative_to(self.cfg.music_root).as_posix() for p in self.cfg.music_root.rglob("*"))
        self.assertEqual(vorher, nachher)


class Bindung(Fall):
    def test_nur_loopback(self):
        for host in ("0.0.0.0", "localhost", "192.168.1.5", ""):
            cfg = Config(self.cfg.music_root, self.cfg.data_dir, 0, host)
            with self.assertRaises(Ablehnung) as ctx:
                make_server(cfg, port=0)
            self.assertEqual(ctx.exception.code, "invalid_bind")


class OhneMusikordner(ServerFall):
    musik = False

    def test_katalog_meldet_fehler_weg2_geht(self):
        status, katalog, _ = self.http("GET", "/api/catalog")
        self.assertEqual((status, katalog["error"]), (200, "music_root_missing"))
        self.assertFalse(self.http("GET", "/api/health")[1]["music_root_vorhanden"])
        status, order, _ = self.http("POST", "/api/auftraege", {"weg": "beschreibung", "artist_slug": "cco", "wunsch": "x"})
        self.assertEqual(status, 201)
        status, order, _ = self.http("POST", f"/api/auftraege/{order['id']}/abschicken", {"revision": 1})
        self.assertEqual((status, order["status"]), (200, "offen"))


if __name__ == "__main__":
    unittest.main()
