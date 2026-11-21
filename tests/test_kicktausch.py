"""Kick-Tausch: Klangrechnung an nachgebauten Spuren und der Ablauf im Dienst mit nachgestellter Stem-Trennung."""
import importlib.util
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path

from hilfe import TIDY1, TIDY2, ServerFall

DSP = Path(__file__).resolve().parent.parent / "sirens" / "kick_dsp.py"
KLANG = all(importlib.util.find_spec(m) for m in ("numpy", "scipy", "soundfile"))
RATE = 22050


def kick(np, grundton, laenge, staerke=1.0):
    t = np.arange(int(laenge * RATE)) / RATE
    ton = grundton * (1 + 1.5 * np.exp(-t / 0.012))          # Anschlag fällt schnell auf den Grundton
    return staerke * np.sin(2 * np.pi * np.cumsum(ton) / RATE) * np.exp(-t / (laenge / 4))


def spur(np, dauer, schlaege, grundton, laenge):
    """Schlagzeugspur: Kicks an den genannten Stellen (Sekunde, Stärke) und durchgehend leise Hi-Hats."""
    x = np.zeros(int(dauer * RATE))
    for sekunde, staerke in schlaege:
        k = kick(np, grundton, laenge, staerke)
        a = int(sekunde * RATE)
        x[a: a + len(k)] += k[: len(x) - a]
    zufall = np.random.default_rng(1).standard_normal(len(x))
    hats = np.diff(zufall, prepend=0) * 0.03 * (np.arange(len(x)) % (RATE // 4) < RATE // 40)  # Zischen in jedem Viertel
    return np.stack([x + hats, x + hats], axis=1).astype("float32")


@unittest.skipUnless(KLANG, "numpy, scipy und soundfile sind nicht installiert")
class Klangrechnung(unittest.TestCase):
    def test_pausen_staerken_und_stimmung_kommen_vom_zielsong(self):
        import numpy as np
        import soundfile as sf
        import tempfile
        # Zielsong: 120 BPM, acht leise Schläge, zwei Sekunden Pause, dann acht laute; Kick auf 56 Hz
        ziel = [(0.5 * i, 0.35) for i in range(8)] + [(6.0 + 0.5 * i, 0.9) for i in range(8)]
        # Spender: 100 BPM, anderer Klang (45 Hz, langer Ausklang), erst leise, dann laut
        spender = [(0.6 * i, 0.3) for i in range(12)] + [(7.2 + 0.6 * i, 0.8) for i in range(14)]
        with tempfile.TemporaryDirectory() as ordner:
            o = Path(ordner)
            drums_ziel = spur(np, 10.5, ziel, 56, 0.25)
            bass = (0.2 * np.sin(2 * np.pi * 110 * np.arange(len(drums_ziel)) / RATE)).astype("float32")
            sf.write(o / "dz.wav", drums_ziel, RATE)
            sf.write(o / "rz.wav", np.stack([bass, bass], axis=1), RATE)
            sf.write(o / "ds.wav", spur(np, 16, spender, 45, 0.5), RATE)
            lauf = subprocess.run([sys.executable, str(DSP), str(o / "dz.wav"), str(o / "rz.wav"), str(o / "ds.wav"), str(o / "aus.wav")],
                                  capture_output=True, text=True, encoding="utf-8", timeout=120)
            self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)
            bericht = json.loads(lauf.stdout)
            aus, _ = sf.read(o / "aus.wav", dtype="float32")
        self.assertEqual((bericht["treffer_ziel"], bericht["treffer_spender"]), (16, 26))
        self.assertEqual(len(bericht["pausen"]), 1)                       # die Pause des Zielsongs ist erkannt …
        self.assertTrue(3.4 <= bericht["pausen"][0][0] <= 3.6 and 5.9 <= bericht["pausen"][0][1] <= 6.1)
        self.assertAlmostEqual(bericht["halbtoene"], 3.8, delta=0.7, msg=str(bericht))  # 45 Hz → 56 Hz
        self.assertGreater(bericht["muster"], 1)                          # leises und lautes Muster des Spenders
        from sirens.kick_dsp import tief
        pause = slice(int(4.3 * RATE), int(5.9 * RATE))                   # dort klingt nur der Bass: daran die Gesamtlautstärke ablesen
        faktor = float(np.dot(aus[pause, 0], bass[pause]) / np.dot(bass[pause], bass[pause]))
        neu = aus[:, 0] - faktor * bass[: len(aus)]                       # ohne den Bass bleibt das Schlagzeug
        unten = tief(neu, RATE)                                           # nur der Tiefton: dort sitzt die Kick, nicht die Hi-Hat
        pegel = lambda a, b, x=neu: float(np.sqrt(np.mean(x[int(a * RATE): int(b * RATE)] ** 2)))
        self.assertLess(pegel(4.3, 5.9, unten), 0.05 * pegel(6.0, 6.3, unten))  # … und bleibt ohne Kick
        self.assertGreater(pegel(6.0, 6.3), 1.8 * pegel(0.0, 0.3))        # laute Stelle bleibt lauter als die leise
        # der Klang ist der des Spenders: der Schlag klingt länger aus als die kurze Kick des Zielsongs
        alt = drums_ziel[:, 0]
        ausklang = lambda x: float(np.sqrt(np.mean(x[int(6.2 * RATE): int(6.4 * RATE)] ** 2)) / np.sqrt(np.mean(x[int(6.0 * RATE): int(6.1 * RATE)] ** 2)))
        self.assertGreater(ausklang(neu), 2 * ausklang(alt))

    def test_ohne_kick_gibt_es_eine_klare_meldung(self):
        import numpy as np
        import soundfile as sf
        import tempfile
        with tempfile.TemporaryDirectory() as ordner:
            o = Path(ordner)
            still = np.zeros((RATE * 3, 2), "float32")
            sf.write(o / "still.wav", still, RATE)
            sf.write(o / "ds.wav", spur(np, 4, [(0.5 * i, 0.8) for i in range(7)], 50, 0.3), RATE)
            lauf = subprocess.run([sys.executable, str(DSP), str(o / "still.wav"), str(o / "still.wav"), str(o / "ds.wav"), str(o / "aus.wav")],
                                  capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(lauf.returncode, 1)
        self.assertIn("Zielsong", json.loads(lauf.stdout)["error"])


class Ablauf(ServerFall):
    def test_nicht_eingerichtet_und_falsche_eingaben(self):
        self.server.app.kick.env = {}                                   # weder Befehl noch (sicher) demucs
        import sirens.kicktausch as modul
        if modul.stems_befehl({}) is None:
            self.assertEqual(self.http("GET", "/api/einstellungen")[1]["kicktausch"], False)
            self.assertEqual(self.http("POST", "/api/kicktausch", {"ziel": TIDY1, "spender": TIDY2})[0], 409)
        self.assertEqual(self.http("POST", "/api/kicktausch", {"ziel": TIDY1, "spender": "cco/fehlt.mp3"})[0], 400)
        self.assertEqual(self.http("POST", "/api/kicktausch", {"ziel": TIDY1, "spender": TIDY1})[0], 400)
        self.assertEqual(self.http("GET", "/api/kicktausch?id=gibtsnicht")[0], 404)
        self.assertEqual(modul.stems_befehl({"SIRENS_STEMS_CMD": "kein json"}), None)
        self.assertEqual(modul.stems_befehl({"SIRENS_STEMS_CMD": '["x", "{ein}"]'}), ["x", "{ein}"])

    @unittest.skipUnless(KLANG, "numpy, scipy und soundfile sind nicht installiert")
    def test_tausch_mit_nachgestellter_trennung(self):
        # Die Stem-Trennung wird nachgestellt: ein Skript legt für jeden Song Schlagzeug und Rest als WAV ab.
        skript = self.tmp / "trennen.py"
        skript.write_text(chr(10).join([
            "import math, struct, sys, wave", "from pathlib import Path",
            "aus = Path(sys.argv[2]) / 'htdemucs' / 'song'; aus.mkdir(parents=True)",
            "takt = 0.6 if 'Version 2' in sys.argv[1] else 0.5",
            "def schreiben(name, werte):",
            "    with wave.open(str(aus / name), 'wb') as w:",
            "        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)",
            "        w.writeframes(b''.join(struct.pack('<h', int(v * 30000)) for v in werte))",
            "n = 22050 * 6",
            "schreiben('drums.wav', [0.8 * math.sin(2 * math.pi * 55 * (i / 22050 % takt)) * math.exp(-(i / 22050 % takt) * 14) for i in range(n)])",
            "schreiben('no_drums.wav', [0.1 * math.sin(2 * math.pi * 220 * i / 22050) for i in range(n)])"]), encoding="utf-8")
        self.server.app.kick.env = {"SIRENS_STEMS_CMD": json.dumps([sys.executable, str(skript), "{ein}", "{aus}"])}
        self.assertEqual(self.http("GET", "/api/einstellungen")[1]["kicktausch"], True)
        status, job, _ = self.http("POST", "/api/kicktausch", {"ziel": TIDY1, "spender": TIDY2})
        self.assertEqual((status, job["stand"] in ("wartet", "laeuft", "fertig")), (202, True))
        for _ in range(200):
            job = self.http("GET", f"/api/kicktausch?id={job['id']}")[1]
            if job["stand"] in ("fertig", "fehler"):
                break
            time.sleep(0.1)
        self.assertEqual(job["stand"], "fertig", job)
        self.assertEqual(job["bericht"]["treffer_ziel"], 12)             # sechs Sekunden, alle 0,5 s ein Schlag
        status, daten, kopf = self.http("GET", f"/api/kicktausch/audio?id={job['id']}", roh=True)
        self.assertEqual((status, daten[:4], kopf["Content-Type"]), (200, b"RIFF", "audio/wav"))
        ablage = self.cfg.data_dir / "spielzeug"
        self.assertEqual(len(list((ablage / "stems").iterdir())), 2)     # je Song einmal getrennt …
        self.assertFalse(any(self.cfg.music_root.rglob("*.wav")) and any("spielzeug" in str(p) for p in self.cfg.music_root.rglob("*")))
        zweiter = self.http("POST", "/api/kicktausch", {"ziel": TIDY1, "spender": TIDY2})[1]
        self.assertEqual((zweiter["id"], zweiter["stand"]), (job["id"], "fertig"))  # … und das Ergebnis wird wiederverwendet


class Einstellungen(unittest.TestCase):
    def test_env_datei_gilt_fuer_den_dienst_aber_gesetztes_bleibt(self):
        import os
        import tempfile
        from pathlib import Path
        from sirens import config
        with tempfile.TemporaryDirectory() as ordner:
            datei = Path(ordner) / ".env"
            datei.write_text(chr(10).join(["# Kommentar", "GEHEIM=nicht fuer den Dienst", "SIRENS_PROBE_A=aus der Datei",
                                           "SIRENS_PROBE_B=aus der Datei"]), encoding="utf-8")
            os.environ["SIRENS_PROBE_B"] = "schon gesetzt"
            try:
                config.aus_datei_setzen(datei)
                self.assertEqual(os.environ.get("SIRENS_PROBE_A"), "aus der Datei")
                self.assertEqual(os.environ.get("SIRENS_PROBE_B"), "schon gesetzt")
                self.assertNotIn("GEHEIM", os.environ)                    # Zugangsdaten bleiben in der Datei
            finally:
                os.environ.pop("SIRENS_PROBE_A", None)
                os.environ.pop("SIRENS_PROBE_B", None)


if __name__ == "__main__":
    unittest.main()
