"""Optionales Instrument-Labor: Notenstatus, Transkriptions-Cache und GPU-Schutz."""
import json
import time
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

from hilfe import ServerFall, TIDY1
from sirens.stems import MODELLE


class InstrumentLaborAPI(ServerFall):
    def vorbereitet(self):
        def faken(cmd, **kwargs):
            modell = cmd[cmd.index("-n") + 1]
            ziel = Path(cmd[cmd.index("-o") + 1]) / modell / Path(cmd[-1]).stem
            ziel.mkdir(parents=True, exist_ok=True)
            for name in MODELLE[modell]:
                (ziel / (name + ".wav")).write_bytes(b"RIFF1234WAVE")
            return type("Ergebnis", (), {"returncode": 0})()

        with patch("sirens.stems.subprocess.run", side_effect=faken):
            self.assertIn(self.http("POST", "/api/stems", {"pfad": TIDY1})[0], (200, 202))
            ende = time.monotonic() + 4
            while time.monotonic() < ende:
                zustand = self.http("GET", "/api/stems?pfad=" + quote(TIDY1))[1]["zustand"]
                if zustand != "laeuft":
                    self.assertEqual(zustand, "bereit")
                    return
                time.sleep(.03)
        self.fail("Demucs-Testvorbereitung überschritt Zeitlimit.")

    @staticmethod
    def url(stem="bass"):
        return "/api/stems/notes?pfad=" + quote(TIDY1) + "&modell=htdemucs&stem=" + stem

    def warten(self, stem="bass"):
        ende = time.monotonic() + 4
        while time.monotonic() < ende:
            daten = self.http("GET", self.url(stem))[1]
            if daten["zustand"] != "laeuft":
                return daten
            time.sleep(.02)
        self.fail("Basic-Pitch-Test überschritt Zeitlimit.")

    def test_status_und_sichere_dateien(self):
        self.assertEqual(self.http("GET", self.url())[0], 409)
        self.vorbereitet()
        self.assertEqual(self.http("GET", self.url())[1]["zustand"], "offen")
        self.assertEqual(self.http("GET", self.url("../bass"))[0], 400)
        self.assertEqual(self.http("POST", "/api/stems/notes", {"pfad": TIDY1, "stem": "foo"})[0], 400)
        self.assertEqual(self.http("POST", "/api/stems/notes", ["invalid"])[0], 400)

    def test_note_events_cache_und_status(self):
        self.vorbereitet()
        noten = [[0.1, 0.4, 65, .7], [1, 1.8, 70, .85]]

        def fake_worker(args, **kwargs):
            Path(args[-1]).write_text(json.dumps(noten), encoding="utf-8")
            return type("Ergebnis", (), {"returncode": 0})()

        with patch("sirens.stem_notes.subprocess.run", side_effect=fake_worker) as run:
            self.assertIn(self.http("POST", "/api/stems/notes", {"pfad": TIDY1, "stem": "bass"})[0], (200, 202))
            result = self.warten()
            self.assertEqual(result["noten"], noten)
            self.assertEqual(result["zustand"], "bereit")
            self.assertEqual(run.call_count, 1)
            self.assertEqual(self.http("POST", "/api/stems/notes", {"pfad": TIDY1, "stem": "bass"})[0], 200)
            self.assertEqual(run.call_count, 1)

    def test_note_worker_fehlermeldung(self):
        self.vorbereitet()
        with patch("sirens.stem_notes.subprocess.run",
                   return_value=type("Ergebnis", (), {"returncode": 42})()):
            self.assertIn(self.http("POST", "/api/stems/notes", {"pfad": TIDY1, "stem": "bass"})[0], (200, 202))
            self.assertEqual(self.warten()["zustand"], "fehler")

    def test_cuda_waehrend_claude_lauf_abgelehnt(self):
        with patch.object(self.server.app.starter, "zustand", return_value={"laeuft": True}):
            code, daten, _ = self.http("POST", "/api/stems",
                                       {"pfad": TIDY1, "modell": "htdemucs", "device": "cuda"})
            self.assertEqual((code, daten["error"]), (409, "busy_gpu"))
