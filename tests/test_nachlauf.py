"""Nachlauf: Favorit fertig machen (Mastering, Ableton, Cover, Text, SoundCloud)."""
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from hilfe import TIDY1, TIDY2, Fall, ServerFall

from sirens import studio
from sirens.contracts import Ablehnung
from sirens.nachlauf import NachlaufAktionen
from sirens.workflow import lage

EMASTERED = "cco/lab-notes/mastered/Too Tidy - Version 1 PreMix (eMastered).wav"
COVER = "cco/lab-notes/cover.png"
TEXT = "cco/lab-notes/Too Tidy - Beschreibung.txt"


def stand(order):
    return lage(order)["dran"], lage(order)["station"]


class Ablauf(Fall):
    def setUp(self):
        super().setUp()
        self.nach = NachlaufAktionen(self.cfg, self.store)
        (self.cfg.music_root / TEXT).write_text("Ein Song über Ordnung.\n\n[Verse]\nZeile", encoding="utf-8")

    def start(self):
        order = self.fertiger_auftrag()
        return self.nach.start(order["id"], {"revision": order["revision"], "pfad": TIDY1})

    def tun(self, name, order, **body):
        return getattr(self.nach, name)(order["id"], {"revision": order["revision"], **body})

    def test_ganzer_weg(self):
        order = self.start()
        oid = order["id"]
        self.assertEqual(stand(order), ("nutzer", 6))
        self.assertEqual(self.claude.todo(), [])
        self.assertEqual(self.claude.show(oid)["nachlauf_info"]["kandidaten"], [EMASTERED])
        with self.assertRaises(Ablehnung):
            self.tun("master", order, weg="datei", datei=TIDY2)  # kein Master zu diesem Song
        order = self.tun("master", order, weg="datei", datei=EMASTERED)
        self.assertEqual(stand(order), ("claude", 7))
        self.assertEqual(self.claude.todo()[0]["gruende"], ["Nachlauf: cover", "Nachlauf: text"])
        self.assertEqual(self.claude.show(oid)["nachlauf_info"]["endfassung"], EMASTERED)

        self.cli("phase", oid, "--name", "soundcloud", "--link", "https://soundcloud.com/x", ok=False)  # kein Ja
        self.cli("phase", oid, "--name", "cover", "--file", TIDY1, ok=False)  # kein Bild
        self.cli("phase", oid, "--name", "cover", "--file", COVER)
        order = self.cli("phase", oid, "--name", "text", "--file", TEXT, "--tag", "funk", "--tag", "electro")
        self.assertEqual(order["nachlauf"]["text"]["tags"], ["funk", "electro"])
        self.assertIn("Ordnung", order["nachlauf"]["text"]["beschreibung"])
        order = self.store.load(oid)
        self.assertEqual(stand(order), ("nutzer", 7))

        order = self.tun("cover", order, entscheidung="neu", text="dunkler")
        self.assertEqual(lage(order)["dran"], "claude")
        self.cli("phase", oid, "--name", "cover", "--file", COVER)
        order = self.tun("cover", self.store.load(oid), entscheidung="annehmen")
        self.assertEqual(stand(order), ("nutzer", 9))

        order = self.tun("ableton", order)
        self.assertTrue(lage(order)["claude_auch_dran"])
        self.cli("phase", oid, "--name", "ableton", "--text", "Spur Too Tidy")
        with self.assertRaises(Ablehnung):  # ohne ausdrückliche Bestätigung kein Upload
            self.tun("soundcloud", self.store.load(oid), entscheidung="hochladen", sichtbarkeit="oeffentlich")
        order = self.tun("soundcloud", self.store.load(oid), entscheidung="hochladen", sichtbarkeit="oeffentlich", bestaetigt=True,
                         promotion=True)
        self.assertEqual(lage(order)["dran"], "claude")
        self.cli("phase", oid, "--name", "soundcloud", "--link", "http://unsicher", ok=False)
        self.cli("phase", oid, "--name", "soundcloud", "--link", "https://soundcloud.com/cco/too-tidy")
        order = self.store.load(oid)
        self.assertEqual((*stand(order), lage(order)["ausgelassen"]), ("nutzer", 10, []))
        order = self.nutzer.close(oid, {"revision": order["revision"]})
        self.assertEqual((order["status"], lage(order)["ausgelassen"]), ("abgeschlossen", []))

    def test_auslassen_und_fehler(self):
        order = self.start()
        oid = order["id"]
        self.tun("master", order, weg="ohne")
        self.cli("phase", oid, "--name", "cover", "--fehler", "Bilddienst antwortet nicht")
        order = self.store.load(oid)
        self.assertEqual(order["nachlauf"]["cover"]["stand"], "wartet")
        with self.assertRaises(Ablehnung):
            self.tun("cover", order, entscheidung="annehmen")
        self.tun("cover", order, entscheidung="ohne")
        self.cli("phase", oid, "--name", "text", "--file", TEXT)
        order = self.tun("soundcloud", self.store.load(oid), entscheidung="ohne")
        self.assertEqual(lage(order)["ausgelassen"], [6, 7, 9])
        order = self.nutzer.close(oid, {"revision": order["revision"]})
        self.assertEqual(lage(order)["ausgelassen"], [6, 7, 9])

    def test_cover_nach_dem_upload_aendern(self):
        order = self.tun("master", self.start(), weg="ohne")
        oid = order["id"]
        self.cli("phase", oid, "--name", "cover", "--file", COVER)
        self.cli("phase", oid, "--name", "text", "--file", TEXT)
        order = self.tun("cover", self.store.load(oid), entscheidung="annehmen")
        order = self.tun("soundcloud", order, entscheidung="hochladen", bestaetigt=True)
        self.assertNotIn("Promotion", order["verlauf"][-1]["text"])
        with self.assertRaises(Ablehnung):
            self.tun("cover", order, entscheidung="aendern")  # nicht während des Uploads
        self.cli("phase", oid, "--name", "soundcloud", "--link", "https://soundcloud.com/cco/too-tidy")
        order = self.store.load(oid)
        self.assertEqual(stand(order), ("nutzer", 10))

        frueher = "cco/lab-notes/Too Tidy - Cover (Versuch 1).png"  # ein anderes Bild aus dem Songordner wählen
        (self.cfg.music_root / frueher).write_bytes(b"png")
        self.assertEqual(self.claude.show(oid)["nachlauf_info"]["cover_kandidaten"], [frueher])
        with self.assertRaises(Ablehnung):
            self.tun("cover", order, entscheidung="datei", datei="cco/nebelpuls/cover.png")
        order = self.tun("cover", order, entscheidung="datei", datei=frueher)
        self.assertEqual((order["nachlauf"]["soundcloud"]["cover_offen"], *stand(order)), (True, "nutzer", 9))

        def skript(antwort, code):  # nachgestelltes Upload-Skript
            datei = self.tmp / f"sc{code}.py"
            zeilen = ["import sys", "assert '--replace-cover' in sys.argv and sys.argv[-1].endswith('.png')",
                      "print('Access token refreshed.')", f"print('{antwort}')", f"sys.exit({code})"]
            datei.write_text(chr(10).join(zeilen), encoding="utf-8")
            return patch.dict(os.environ, {"SIRENS_SOUNDCLOUD_CMD": json.dumps([sys.executable, str(datei)])})
        with skript('{"status": "failed", "http_status": 401, "response": "nein"}', 1):
            order = self.tun("soundcloud", order, entscheidung="cover")
        s = order["nachlauf"]["soundcloud"]
        self.assertEqual((s["cover_offen"], "401" in s["cover_fehler"], *stand(order)), (True, True, "nutzer", 9))
        with skript('{"status": "artwork_replaced"}', 0):
            order = self.tun("soundcloud", order, entscheidung="cover")
        s = order["nachlauf"]["soundcloud"]
        self.assertEqual((s["cover_offen"], s["cover_fehler"], *stand(order)), (False, "", "nutzer", 10))

        order = self.tun("cover", order, entscheidung="aendern", text="heller")  # neues Cover von Claude, höchstens fünf je Song
        self.assertEqual((order["nachlauf"]["cover"]["stand"], *stand(order)), ("offen", "claude", 7))
        self.assertEqual(self.claude.todo()[0]["gruende"], ["Nachlauf: cover"])
        for _ in range(4):
            self.cli("phase", oid, "--name", "cover", "--file", COVER)
            order = self.store.load(oid)
            if order["nachlauf"]["cover"]["versuche"] < 5:
                order = self.tun("cover", order, entscheidung="neu")
        self.assertEqual(order["nachlauf"]["cover"]["versuche"], 5)
        for wahl in ("neu", "ohne"):  # Grenze erreicht; „ohne“ geht nicht mehr, der Song liegt schon bei SoundCloud
            with self.assertRaises(Ablehnung):
                self.tun("cover", order, entscheidung=wahl)
        order = self.tun("cover", order, entscheidung="annehmen")
        self.assertTrue(order["nachlauf"]["soundcloud"]["cover_offen"])

    def test_mehrere_songs_und_zurueck_zum_anhoeren(self):
        order = self.tun("master", self.start(), weg="ohne")
        oid = order["id"]
        order = self.tun("anhoeren", order)  # zurück: der Stand bleibt, Claude bleibt dran
        self.assertEqual((order["status"], order["nachlauf"]["favorit"], lage(order)["station"]), ("fertig", TIDY1, 5))
        self.assertEqual(self.claude.todo()[0]["gruende"], ["Nachlauf: cover", "Nachlauf: text"])
        order = self.tun("start", order, pfad=TIDY2)  # zweiter Song; der erste wird zurückgestellt
        self.assertEqual((order["nachlauf"]["favorit"], [n["favorit"] for n in order["nachlauf_weitere"]]), (TIDY2, [TIDY1]))
        self.assertEqual(self.claude.todo()[0]["gruende"], [f"Nachlauf: cover [{TIDY1}]", f"Nachlauf: text [{TIDY1}]"])
        self.assertIn(TIDY1, self.claude.show(oid)["nachlauf_info"]["endfassungen"])
        self.cli("phase", oid, "--name", "cover", "--file", COVER, ok=False)  # bei mehreren Songs nur mit --favorit
        self.cli("phase", oid, "--name", "cover", "--file", COVER, "--favorit", TIDY1)
        order = self.store.load(oid)
        self.assertEqual((order["nachlauf"]["cover"]["stand"], order["nachlauf_weitere"][0]["cover"]["stand"]), ("offen", "wartet"))
        self.assertIn("(Too Tidy)", order["verlauf"][-1]["text"])
        order = self.tun("start", order, pfad=TIDY1)  # zurückwechseln: nichts geht verloren
        self.assertEqual((order["nachlauf"]["cover"]["stand"], [n["favorit"] for n in order["nachlauf_weitere"]]), ("wartet", [TIDY2]))

    def test_fremde_datei_und_falscher_status(self):
        order = self.fertiger_auftrag()
        with self.assertRaises(Ablehnung):
            self.tun("start", order, pfad="cco/nebelpuls/Omen - Version 1.mp3")
        with self.assertRaises(Ablehnung):
            self.tun("master", order, weg="ohne")
        geschlossen = self.nutzer.close(order["id"], {"revision": order["revision"]})
        self.assertEqual(lage(geschlossen)["ausgelassen"], [6, 7, 8, 9])
        self.assertEqual(self.tun("start", geschlossen, pfad=TIDY2)["status"], "nachlauf")


class NurMastern(ServerFall):
    def test_vorhandenen_song_mastern_und_im_explorer_zeigen(self):
        status, order, _ = self.http("POST", "/api/mastern", {"pfad": TIDY1})
        self.assertEqual((status, order["status"], order["lage"]["dran"], order["lage"]["station"]), (201, "nachlauf", "nutzer", 6))
        self.assertEqual(order["lage"]["ausgelassen"], [2, 3, 4, 5, 7, 8, 9])
        self.assertEqual(order["nachlauf_info"]["kandidaten"], [EMASTERED])
        self.assertEqual(self.claude.todo(), [])
        adresse = f"/api/auftraege/{order['id']}/"
        _, order, _ = self.http("POST", adresse + "master", {"revision": order["revision"], "weg": "datei", "datei": EMASTERED})
        self.assertEqual((order["lage"]["dran"], order["lage"]["station"]), ("nutzer", 10))
        self.assertEqual(self.claude.todo(), [])
        status, order, _ = self.http("POST", adresse + "abschliessen", {"revision": order["revision"]})
        self.assertEqual((status, order["status"]), (200, "abgeschlossen"))
        self.assertEqual(self.http("POST", "/api/mastern", {"pfad": "cco/fehlt.mp3"})[0], 400)
        self.assertEqual(self.http("POST", "/api/mastern", {"pfad": TIDY1, "schritte": ["tanzen"]})[0], 400)
        _, nur_cover, _ = self.http("POST", "/api/mastern", {"pfad": TIDY2, "schritte": ["cover", "text"]})
        self.assertEqual((nur_cover["lage"]["dran"], nur_cover["lage"]["ausgelassen"]), ("claude", [2, 3, 4, 5, 6, 9]))
        self.assertEqual(self.claude.todo()[0]["gruende"], ["Nachlauf: cover", "Nachlauf: text"])
        _, nur_ableton, _ = self.http("POST", "/api/mastern", {"pfad": TIDY2, "schritte": []})
        _, nur_ableton, _ = self.http("POST", f"/api/auftraege/{nur_ableton['id']}/ableton", {"revision": nur_ableton["revision"]})
        self.assertEqual(nur_ableton["nachlauf"]["ableton"]["stand"], "beauftragt")

        import os
        import sys
        marke = self.tmp / "gezeigt.txt"
        os.environ["SIRENS_EXPLORER_CMD"] = json.dumps(
            [sys.executable, "-c", "import sys, pathlib; pathlib.Path(sys.argv[1]).write_text(sys.argv[2], encoding='utf-8')", str(marke)])
        self.addCleanup(os.environ.pop, "SIRENS_EXPLORER_CMD", None)
        status, antwort, _ = self.http("POST", "/api/explorer", {"pfad": TIDY1})
        self.assertEqual(status, 200, antwort)
        for _ in range(50):
            if marke.exists():
                break
            time.sleep(0.1)
        self.assertTrue(marke.read_text(encoding="utf-8").endswith("Too Tidy - Version 1.mp3"))
        self.assertEqual(self.http("POST", "/api/explorer", {"pfad": "../geheim.mp3"})[0], 400)
        self.assertEqual(self.http("POST", "/api/explorer", {"pfad": "cco/fehlt.mp3"})[0], 404)


class Detail(Fall):
    def arten(self, **wunsch):
        from sirens import ablauf
        return {s["name"]: s["art"] for s in ablauf.plan(wunsch)}

    def test_plan_zeigt_was_fast_mode_auslaesst(self):
        normal = self.arten(umfang="album", optionen={"planfreigabe": "an"})
        self.assertEqual(set(normal.values()), {"voll"})
        song = self.arten(umfang="song", optionen={})
        self.assertEqual([n for n, a in song.items() if a == "entfaellt"], ["planfreigabe", "abgleich"])
        schnell = self.arten(umfang="album", optionen={"tempo": "schnell"})
        self.assertEqual([n for n, a in schnell.items() if a == "entfaellt"],
                         ["rueckfrage", "planfreigabe", "abgleich", "zweitgutachten", "korrektur"])
        self.assertEqual([n for n, a in schnell.items() if a == "kurz"], ["konzept", "text", "freigabe"])
        self.assertEqual((schnell["klang"], schnell["senden"]), ("voll", "voll"))

    def test_fortschritt_ueber_die_cli(self):
        order = self.entwurf(optionen={"tempo": "schnell"})
        oid = order["id"]
        self.nutzer.submit(oid, {"revision": order["revision"]})
        self.cli("detail", oid, "--name", "text", ok=False)  # noch nicht übernommen
        self.claude.claim(oid)
        self.cli("detail", oid, "--name", "text")
        stand = {s["name"]: s["zustand"] for s in lage(self.store.load(oid))["detail"]}
        self.assertEqual((stand["lesen"], stand["rueckfrage"], stand["konzept"], stand["text"], stand["paket"]),
                         ("erledigt", "entfaellt", "erledigt", "aktiv", "offen"))
        self.claude.track(oid, 1, "fertig", "Neu", [TIDY1])
        self.claude.sent(oid, "neu")
        stand = {s["name"]: s["zustand"] for s in lage(self.store.load(oid))["detail"]}
        self.assertEqual((stand["senden"], stand["download"]), ("erledigt", "aktiv"))
        fertig = lage(self.claude.done(oid))["detail"]
        self.assertEqual({s["zustand"] for s in fertig}, {"erledigt", "entfaellt"})
        self.assertEqual(lage(self.nach_vorhanden())["detail"], [])

    def nach_vorhanden(self):
        return NachlaufAktionen(self.cfg, self.store).vorhanden({"pfad": TIDY2})


class Regler(unittest.TestCase):
    def test_pruefung_und_kette(self):
        self.assertEqual(studio.kette(studio.einstellungen(None)), [])
        kette = studio.kette(studio.einstellungen({"eq_sub": 3, "eq_praesenz": -2, "komp_an": True, "komp_mitte": 2, "breite": 120}))
        self.assertEqual(kette[0], "bass=g=3.0:f=40:t=q:w=0.7")
        self.assertTrue(kette[2].startswith("acompressor=threshold=0.15849:ratio=2.0"), kette[2])
        self.assertEqual(kette[3], "extrastereo=m=1.2:c=0")
        for falsch in ({"eq_sub": 13}, {"lautheit": -5}, {"unbekannt": 1}, {"breite": True}):
            with self.assertRaises(Ablehnung):
                studio.einstellungen(falsch)


class Auswertung(unittest.TestCase):
    ROH = {"f": {"integrated_lufs": -14.1, "true_peak_dbtp": -0.5, "loudness_range_lu": 5.9, "crest_factor_db": 14.6,
                 "stereo_correlation": 0.86, "stereo_width_ratio": 0.27, "duration_seconds": 250.6, "warnings": [],
                 "spectral_bands_relative_to_mid_db": {"sub": 19.6, "bass": 11.2, "low_mid": 5.2, "mid": 0.0,
                                                       "high_mid": -13.8, "air": -22.1}},
           "cluster": {"cluster": "electronic-club", "curation_status": "initial_estimate", "target_crest_factor_db": 8.0,
                       "target_spectral_bands_relative_to_mid_db": {"sub": 23.5, "bass": 15.7, "low_mid": 3.5, "mid": 0.0,
                                                                    "high_mid": -10.8, "air": -16.1}}}
    PROFIL = {"eq_bands": [{"band": "sub", "gain_db": 3.0}, {"band": "low_mid", "gain_db": -1.66}],
              "multiband": {"low_ratio": 1.99, "mid_ratio": 1.79, "high_ratio": 1.59, "mid_threshold_db": -16.0},
              "saturation_drive_db": 2.0, "stereo_width_target": 1.35, "limiter_ceiling_dbtp": -1.0}

    def test_messwerte_empfehlungen_und_presets(self):
        from sirens import analyse
        roh = {**self.ROH, "profile": {stil[0]: self.PROFIL for stil in analyse.STILE}}
        ergebnis = analyse.auswerten(roh)
        self.assertEqual(ergebnis["messwerte"]["lufs"], -14.1)
        # Vergleich und Empfehlung stützen sich auf die gemessenen eMastered-Paare, nicht auf Bewertungen oder Schätzwerte.
        self.assertEqual(ergebnis["baender"][0], {"name": "eq_sub", "band": "sub", "titel": "Sub", "abstand": -1.8})
        self.assertEqual([p["titel"] for p in ergebnis["presets"]],
                         ["Empfehlung", "Streaming −14", "Genre-Zielbild", "Warm", "Offen", "Laut"])
        werte = ergebnis["presets"][0]["einstellungen"]
        self.assertEqual((werte["eq_sub"], werte["eq_bass"], werte["eq_tiefmitten"], werte["eq_praesenz"], werte["eq_luft"]),
                         (-1.0, 1.0, 0.5, 1.0, 3.0))
        self.assertEqual((werte["komp_an"], werte["komp_tief"], werte["komp_mitte"], werte["komp_hoch"]), (True, 1.9, 1.8, 1.7))
        self.assertEqual((werte["saettigung"], werte["breite"], werte["lautheit"], werte["decke"]), (0.0, 100.0, -10.5, -1.0))
        self.assertEqual(ergebnis["presets"][1]["einstellungen"]["lautheit"], -14.0)
        self.assertEqual(ergebnis["presets"][2]["einstellungen"]["breite"], 135.0)  # Schätzwert der Engine bleibt wählbar
        for preset in ergebnis["presets"]:
            studio.einstellungen(preset["einstellungen"])  # jede Voreinstellung liegt in den Grenzen der Regler
        text = " ".join(ergebnis["empfehlungen"])
        for teil in ("eMastered-Fassungen liegen bei −10,4 LUFS", "Pegeldecke", "Leichte Kompression", "Luft um rund 3,0 dB",
                     "bei 100 %", "12 gemessene Paare", "Schätzwerten"):
            self.assertIn(teil, text)
        hell = {**roh, "f": {**roh["f"], "crest_factor_db": 10.0, "spectral_bands_relative_to_mid_db": {
            **roh["f"]["spectral_bands_relative_to_mid_db"], "air": -13.0}}}
        hell = analyse.auswerten(hell)
        self.assertEqual((hell["presets"][0]["einstellungen"]["eq_luft"], hell["presets"][0]["einstellungen"]["komp_an"]), (0.0, False))
        self.assertIn("Luft liegt hier schon", " ".join(hell["empfehlungen"]))


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg fehlt")
class Rendern(ServerFall):
    def test_studio_master_ueber_die_seite(self):
        quelle = self.cfg.music_root / TIDY1
        quelle.unlink()  # Platzhalter im Testordner durch echten Ton ersetzen
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=4", "-ac", "2",
                        str(quelle)], check=True)
        order = self.fertiger_auftrag()
        adresse = f"/api/auftraege/{order['id']}/"
        _, order, _ = self.http("POST", adresse + "nachlauf", {"revision": order["revision"], "pfad": TIDY1})
        self.assertTrue(order["nachlauf_info"]["werkzeuge"]["ffmpeg"])
        status, order, _ = self.http("POST", adresse + "studio",
                                     {"revision": order["revision"], "einstellungen": {"eq_sub": 4, "lautheit": -12}})
        self.assertEqual(status, 200, order)
        entwurf = order["nachlauf"]["mastering"]["entwuerfe"][0]
        self.assertEqual(entwurf["datei"], "cco/lab-notes/Too Tidy - Version 1 (Studio Master).wav")
        self.assertAlmostEqual(entwurf["lufs"], -12, delta=0.6)
        self.assertLessEqual(entwurf["spitze"], -0.5)
        _, order, _ = self.http("POST", adresse + "studio", {"revision": order["revision"]})
        self.assertTrue(order["nachlauf"]["mastering"]["entwuerfe"][1]["datei"].endswith("(Studio Master 2).wav"))
        self.assertGreater(quelle.stat().st_size, 1000)  # Original unberührt
        status, order, _ = self.http("POST", adresse + "master",
                                     {"revision": order["revision"], "weg": "datei", "datei": entwurf["datei"]})
        self.assertEqual(status, 200)
        self.assertIn(order["nachlauf"]["mastering"]["weg"], ("Studio", "Studio (Engine)"))
        status, _, kopf = self.http("GET", "/api/bild?pfad=cco/lab-notes/cover.png", roh=True)
        self.assertEqual((status, kopf["Content-Type"]), (200, "image/png"))
        self.assertEqual(self.http("GET", "/api/bild?pfad=cco/flach.mp3")[0], 400)


if __name__ == "__main__":
    unittest.main()
