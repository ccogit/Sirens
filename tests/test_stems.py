"""Stem Studio: API, Cache, Demucs-Aufruf und Sicherheitsgrenzen ohne echtes KI-Modell."""
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

from hilfe import ServerFall, TIDY1, TIDY2
from sirens.stems import MODELLE


class StemAPI(ServerFall):
    def url(self, pfad=TIDY1, modell="htdemucs", stem=None):
        werte = "?pfad=" + quote(pfad, safe="") + "&modell=" + quote(modell)
        return "/api/stems" + ("/audio" if stem else "") + werte + (
            "&stem=" + quote(stem) if stem else ""
        )

    def warten(self, pfad=TIDY1, modell="htdemucs"):
        ende = time.monotonic() + 5
        while time.monotonic() < ende:
            antwort = self.http("GET", self.url(pfad, modell))[1]
            if antwort["zustand"] != "laeuft":
                return antwort
            time.sleep(.025)
        self.fail("Stem-Lauf hat nicht geendet.")

    @staticmethod
    def demucs_ersetzen(cmd, **kwargs):
        modell = cmd[cmd.index("-n") + 1]
        ziel = Path(cmd[cmd.index("-o") + 1]) / modell / Path(cmd[-1]).stem
        ziel.mkdir(parents=True)
        for stem in MODELLE[modell]:
            (ziel / (stem + ".wav")).write_bytes(b"WAVE-0123456789")
        return type("Ergebnis", (), {"returncode": 0})()

    def test_status_validation_und_sicherheit(self):
        status, daten, _ = self.http("GET", self.url())
        self.assertEqual((status, daten["zustand"], len(daten["stems"])), (200, "offen", 4))
        self.assertEqual(self.http("GET", self.url(stem="vocals"))[0], 409)
        for pfad in ("../geheim.mp3", "/etc/passwd.mp3", "C:/Songs/song.mp3"):
            self.assertEqual(self.http("GET", self.url(pfad))[0], 400)
        self.assertEqual(self.http("GET", self.url(modell="x"))[0], 400)
        self.assertEqual(self.http("GET", self.url(stem="../vocals"))[0], 400)
        self.assertEqual(self.http("GET", self.url("fehlt.wav"))[0], 404)
        self.assertEqual(self.http("POST", "/api/stems", {"pfad": TIDY1, "device": "gpu"})[0], 400)
        self.assertEqual(self.http("POST", "/api/stems", {"pfad": TIDY1, "modell": "x"})[0], 400)
        self.assertEqual(self.http("POST", "/api/stems", ["invalid"])[0], 400)

    def test_ki_trennung_cache_und_streaming(self):
        with patch("sirens.stems.subprocess.run", side_effect=self.demucs_ersetzen) as lauf:
            code, daten, _ = self.http("POST", "/api/stems", {"pfad": TIDY1, "modell": "htdemucs_6s", "device": "cuda"})
            self.assertIn(code, (200, 202))
            self.assertIn(daten["zustand"], ("laeuft", "bereit"))
            ergebnis = self.warten(modell="htdemucs_6s")
            self.assertEqual((ergebnis["zustand"], len(ergebnis["stems"])), ("bereit", 6))
            self.assertEqual(lauf.call_count, 1)
            cmd = lauf.call_args.args[0]
            self.assertEqual(cmd[cmd.index("--device") + 1], "cuda")
            self.assertEqual(cmd[cmd.index("-n") + 1], "htdemucs_6s")
            status, wav, kopf = self.http("GET", self.url(modell="htdemucs_6s", stem="piano"), roh=True)
            self.assertEqual((status, wav), (200, b"WAVE-0123456789"))
            self.assertEqual(kopf["Content-Type"], "audio/wav")
            status, wav, kopf = self.http("GET", self.url(modell="htdemucs_6s", stem="guitar"),
                                         headers={"Range": "bytes=5-8"}, roh=True)
            self.assertEqual((status, wav, kopf["Content-Range"]), (206, b"0123", "bytes 5-8/15"))
            self.assertEqual(self.http("POST", "/api/stems", {"pfad": TIDY1, "modell": "htdemucs_6s"})[0], 200)
            self.assertEqual(lauf.call_count, 1)
            # Neue Quelldatei muss eine neue Trennung bekommen statt alten Cache zu liefern.
            datei = self.cfg.music_root / TIDY1
            datei.write_bytes(b"neue-fassung")
            self.assertEqual(self.http("GET", self.url(modell="htdemucs_6s"))[1]["zustand"], "offen")
            self.assertEqual(self.http("GET", self.url(modell="htdemucs_6s", stem="piano"))[0], 409)

    def test_kein_paralleler_lauf(self):
        laufend = threading.Event()
        freigabe = threading.Event()

        def blockieren(cmd, **kwargs):
            laufend.set()
            if not freigabe.wait(4):
                raise RuntimeError("Testzeitlimit")
            return self.demucs_ersetzen(cmd, **kwargs)

        try:
            with patch("sirens.stems.subprocess.run", side_effect=blockieren):
                self.assertEqual(self.http("POST", "/api/stems", {"pfad": TIDY1})[0], 202)
                self.assertTrue(laufend.wait(2))
                code, daten, _ = self.http("POST", "/api/stems", {"pfad": TIDY2})
                self.assertEqual((code, daten["error"]), (409, "busy"))
                self.assertEqual(self.http("POST", "/api/stems", {"pfad": TIDY1})[0], 202)
                freigabe.set()
                self.assertEqual(self.warten()["zustand"], "bereit")
        finally:
            freigabe.set()

    def test_fehler_nach_trennung_sichtbar(self):
        with patch("sirens.stems.subprocess.run", return_value=type("Ergebnis", (), {"returncode": 13})()):
            self.assertIn(self.http("POST", "/api/stems", {"pfad": TIDY1})[0], (200, 202))
            daten = self.warten()
            self.assertEqual(daten["zustand"], "fehler")
            self.assertIn("demucs.log", daten["meldung"])
            self.assertEqual(self.http("GET", self.url(stem="vocals"))[0], 409)


if __name__ == "__main__":
    unittest.main()
