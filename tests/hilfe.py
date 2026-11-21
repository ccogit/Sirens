"""Gemeinsame Testumgebung: temporäre Ablage und ein kleiner nachgebauter Musikordner (Platzhalterdateien)."""
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sirens import cli  # noqa: E402
from sirens.arbeit import ClaudeAktionen  # noqa: E402
from sirens.config import Config  # noqa: E402
from sirens.server import make_server  # noqa: E402
from sirens.service import NutzerAktionen  # noqa: E402
from sirens.store import Store  # noqa: E402

TIDY1 = "cco/lab-notes/Too Tidy - Version 1.mp3"
TIDY2 = "cco/lab-notes/Too Tidy - Version 2.mp3"
FUGUE = "cco/lab-notes/Fugue State - Version 1.mp3"
OMEN = "cco/nebelpuls/Omen - Version 1.mp3"
MUSIK = [TIDY1, TIDY2, FUGUE, OMEN,
         "cco/lab-notes/mastered/Too Tidy - Version 1 PreMix (eMastered).wav",
         "cco/lab-notes/alt/tief/Loser Name.mp3",
         "anna/erstes/Hallo - Version 1.mp3",
         "cco/flach.mp3", "stamm.json", "cco/lab-notes/cover.png", "cco/lab-notes/Too Tidy - Version 1.asd"]


class Fall(unittest.TestCase):
    musik = True

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.cfg = Config(music_root=self.tmp / "musik", data_dir=self.tmp / "daten", port=0)
        if self.musik:
            for rel in MUSIK:
                datei = self.cfg.music_root / rel
                datei.parent.mkdir(parents=True, exist_ok=True)
                datei.write_bytes(b"0123456789")
        self.store = Store(self.cfg)
        self.nutzer = NutzerAktionen(self.cfg, self.store)
        self.claude = ClaudeAktionen(self.cfg, self.store)
        self.env = {"SIRENS_MUSIC_ROOT": str(self.cfg.music_root),
                    "SIRENS_DATA_DIR": str(self.cfg.data_dir)}

    def cli(self, *argv, ok=True):
        out = io.StringIO()
        code = cli.main(list(argv), env=self.env, out=out)
        data = json.loads(out.getvalue())
        self.assertEqual(code == 0, ok, data)
        return data

    def ablage(self):
        """Inhalt aller Auftragsdateien, um „keine Änderung an der Ablage“ zu prüfen."""
        ordner = self.cfg.orders_dir
        return {p.name: p.read_text(encoding="utf-8") for p in sorted(ordner.glob("*"))} if ordner.is_dir() else {}

    def entwurf(self, **wunsch):
        basis = {"weg": "referenz", "artist_slug": "cco", "referenzen": [{"pfad": TIDY1}]}
        return self.nutzer.create_draft({**basis, **wunsch})

    def fertiger_auftrag(self, dateien=(TIDY1, TIDY2)):
        order = self.entwurf()
        oid = order["id"]
        self.nutzer.submit(oid, {"revision": order["revision"]})
        self.claude.claim(oid)
        self.claude.track(oid, 1, "fertig", "Neu", list(dateien))
        self.claude.sent(oid, "neues-release")
        return self.claude.done(oid)


class ServerFall(Fall):
    def setUp(self):
        super().setUp()
        self.server = make_server(self.cfg, port=0)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.server.app.katalog.warten()
        self.basis = f"http://127.0.0.1:{self.server.server_port}"

    def http(self, methode, pfad, body=None, headers=None, roh=False):
        """Liefert (Status, Antwort, Header). Antwort ist JSON, mit roh=True Bytes."""
        kopf = {"Content-Type": "application/json"} if body is not None else {}
        kopf.update(headers or {})
        daten = json.dumps(body).encode() if body is not None else None
        anfrage = urllib.request.Request(self.basis + pfad, data=daten, method=methode, headers=kopf)
        try:
            with urllib.request.urlopen(anfrage, timeout=10) as antwort:
                status, inhalt, kopfzeilen = antwort.status, antwort.read(), antwort.headers
        except urllib.error.HTTPError as exc:
            status, inhalt, kopfzeilen = exc.code, exc.read(), exc.headers
        return status, (inhalt if roh else json.loads(inhalt or b"{}")), kopfzeilen
