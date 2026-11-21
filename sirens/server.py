"""HTTP-API und Auslieferung der Seite. Bindet ausschließlich an 127.0.0.1."""
import json
import os
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .catalog import Katalog, bekannte_bewertungen, richtungswoerter
from .config import LOOPBACK
from . import ablauf, nachlauf
from .contracts import BILD_EXT, Ablehnung, safe_audio_path
from .service import NutzerAktionen
from .starter import SATZ, ClaudeStarter
from .stems import StemDienst
from .store import Store
from .workflow import lage

WEB = Path(__file__).resolve().parent.parent / "web"
TYPEN = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
         ".svg": "image/svg+xml", ".mp3": "audio/mpeg", ".wav": "audio/wav"}
BILDER = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MAX_BODY = 1_000_000
UEBERGABEN = ("abschicken", "antwort", "plan", "abschliessen", "nachlauf", "master", "ableton", "cover",
              "soundcloud", "textedit")
AUFTRAG = re.compile(r"^/api/auftraege/(SA-\d{8}-\d{3})(?:/([a-z]+))?$")


class App:
    def __init__(self, cfg):
        self.cfg, self.store, self.katalog = cfg, Store(cfg), Katalog(cfg)
        self.nutzer = NutzerAktionen(cfg, self.store)
        self.aktionen = {"abschicken": self.nutzer.submit, "antwort": self.nutzer.answer,
                         "plan": self.nutzer.plan_decision, "bewertung": self.nutzer.rate,
                         "abschliessen": self.nutzer.close, "abbrechen": self.nutzer.cancel}
        nach = self.nach = nachlauf.NachlaufAktionen(cfg, self.store)
        self.aktionen.update(nachlauf=nach.start, anhoeren=nach.anhoeren, analyse=nach.analyse, studio=nach.studio, master=nach.master, ableton=nach.ableton,
                             cover=nach.cover, soundcloud=nach.soundcloud, textedit=nach.text_aendern,
                             version=nach.version)
        self.starter = ClaudeStarter(cfg)
        self.stems = StemDienst(cfg)

    def aktion(self, name, oid, data):
        """Führt eine Nutzeraktion aus und startet Claude, wenn der Auftrag danach bei Claude liegt."""
        order = self.aktionen[name](oid, data)
        stand = lage(order)
        if name in UEBERGABEN and (stand["dran"] == "claude" or stand["claude_auch_dran"]):
            self.starter.starten(f"{oid}: {name}")
        return order

    def voll(self, order):
        return {**order, "lage": lage(order), "claude": self.starter.zustand(),
                "nachlauf_info": nachlauf.info(self.cfg, order) if order["status"] == "nachlauf" else None}

    def _songs(self, order):
        """Kompakte, direkt bearbeitbare Songzeilen statt vollständiger Auftragshistorie."""
        ausgaben = []
        alle = [n for n in (order.get("nachlauf"), *order.get("nachlauf_weitere", [])) if n]
        bewertet = {b["pfad"]: b for b in order.get("bewertungen", [])}
        for t in order.get("tracks_stand", []):
            dateien = t.get("dateien", [])
            if not dateien:
                continue
            pfad = next((p for p in dateien if bewertet.get(p, {}).get("favorit")), dateien[0])
            n = next((n for n in alle if n["favorit"] in dateien), None)
            if n:
                pfad = n["favorit"]
            ausgaben.append({"pfad": pfad, "titel": t.get("titel") or "Song " + str(t["nr"]),
                             "cover": (n or {}).get("cover", {}).get("datei", ""),
                             "soundcloud": (n or {}).get("soundcloud", {}).get("link", ""),
                             "sync_offen": any((n or {}).get("soundcloud", {}).get(k) for k in
                                               ("audio_offen", "cover_offen", "text_offen")),
                             # ohne begonnenes Fertigmachen und ohne Favorit wählt erst der Nutzer den Take
                             "waehlbar": bool(n) or bool(bewertet.get(pfad, {}).get("favorit")),
                             "bearbeitbar": order["status"] in ("fertig", "nachlauf", "abgeschlossen")})
        return ausgaben

    def kurz(self, order):
        frage = next((e["text"] for e in reversed(order["verlauf"]) if e["art"] == "rueckfrage"), "")
        return {"id": order["id"], "status": order["status"], "revision": order["revision"],
                "created_at": order["created_at"], "updated_at": order["updated_at"],
                "vorgaenger_id": order["vorgaenger_id"], "wunsch": order["wunsch"],
                "titel": (order["plan"] or {}).get("titel") or order["wunsch"]["optionen"]["titelwunsch"],
                "frage": frage if order["status"] == "rueckfrage" else "", "lage": lage(order),
                "songs": self._songs(order), "archiviert": len(order.get("archivierte_versionen", []))}

    def health(self, port):
        return {"status": "ok", "pid": os.getpid(), "port": port, "music_root": str(self.cfg.music_root),
                "music_root_vorhanden": self.cfg.music_root.is_dir(), "data_dir": str(self.cfg.data_dir),
                "katalog": self.katalog.zahlen(), "auftraege": len(self.store.list())}


class Handler(BaseHTTPRequestHandler):
    server_version = "SongAuftrag/1"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    @property
    def app(self):
        return self.server.app

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", TYPEN[".json"])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _erlaubte_hosts(self):
        port = self.server.server_port
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _bearbeiten(self, schreibend):
        try:
            if self.headers.get("Host", "") not in self._erlaubte_hosts():
                raise Ablehnung("forbidden_host", "Diese Adresse ist nicht erlaubt.", status=403)
            teile = urlsplit(self.path)
            pfad, query = unquote(teile.path), {k: v[-1] for k, v in parse_qs(teile.query).items()}
            if schreibend:
                self._schreiben(pfad, self._body())
            else:
                self._lesen(pfad, query)
        except Ablehnung as exc:
            self._json(exc.status, exc.as_dict())
        except (ConnectionError, TimeoutError):
            self.close_connection = True
        except Exception:  # noqa: BLE001 – der Dienst soll weiterlaufen
            traceback.print_exc(file=sys.stderr)
            self._json(500, {"error": "internal", "meldung": "Unerwarteter Fehler im Dienst.", "feld": None})

    def do_GET(self):
        self._bearbeiten(False)

    def do_POST(self):
        self._bearbeiten(True)

    do_PUT = do_POST

    def _body(self):
        laenge = int(self.headers.get("Content-Length") or 0)
        roh = self.rfile.read(laenge) if 0 < laenge <= MAX_BODY else b""
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {f"http://{h}" for h in self._erlaubte_hosts()}:
            raise Ablehnung("forbidden_origin", "Anfragen von fremden Seiten werden abgelehnt.", status=403)
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            raise Ablehnung("unsupported_media_type", "Schreibende Anfragen brauchen Content-Type application/json.",
                            status=415)
        if laenge > MAX_BODY:
            self.close_connection = True
            raise Ablehnung("too_large", "Die Anfrage ist zu groß.", status=413)
        try:
            return json.loads(roh.decode("utf-8")) if roh else {}
        except ValueError:
            raise Ablehnung("invalid", "Die Anfrage enthält kein gültiges JSON.") from None

    def _lesen(self, pfad, query):
        app = self.app
        if pfad == "/api/health":
            return self._json(200, app.health(self.server.server_port))
        if pfad == "/api/einstellungen":
            return self._json(200, {"satz": SATZ, "richtungswoerter": richtungswoerter(app.cfg)})
        if pfad == "/api/claude":
            return self._json(200, app.starter.zustand())
        if pfad == "/api/catalog":
            min_score = query.get("min_score")
            if min_score not in (None, ""):
                try:
                    min_score = int(min_score)
                except ValueError:
                    raise Ablehnung("invalid", "„min_score“ muss eine ganze Zahl sein.", "min_score") from None
            else:
                min_score = None
            return self._json(200, app.katalog.baum(bekannte_bewertungen(app.cfg, app.store),
                                                    query.get("q", ""), min_score))
        if pfad == "/api/stems":
            return self._json(200, app.stems.zustand(query.get("pfad"), query.get("modell", "htdemucs")))
        if pfad == "/api/stems/audio":
            datei = app.stems.audiodatei(query.get("pfad"), query.get("modell", "htdemucs"), query.get("stem"))
            return self._audio_datei(datei)
        if pfad == "/api/audio":
            return self._audio(query.get("pfad"))
        if pfad == "/api/bild":
            return self._bild(query.get("pfad"))
        if pfad == "/api/auftraege":
            orders = [app.kurz(o) for o in app.store.list()]
            if query.get("status"):
                orders = [o for o in orders if o["status"] == query["status"]]
            if query.get("dran"):
                orders = [o for o in orders if o["lage"]["dran"] == query["dran"]]
            return self._json(200, {"auftraege": orders, "satz": SATZ, "claude": app.starter.zustand()})
        treffer = AUFTRAG.match(pfad)
        if treffer and not treffer.group(2):
            return self._json(200, app.voll(app.store.load(treffer.group(1))))
        if pfad.startswith("/api/"):
            raise Ablehnung("not_found", "Diese Adresse gibt es nicht.", status=404)
        self._statisch(pfad)

    def _schreiben(self, pfad, data):
        app = self.app
        if self.command == "POST" and pfad == "/api/stems":
            if not isinstance(data, dict):
                raise Ablehnung("invalid", "Die Stem-Anfrage muss ein Objekt sein.")
            stand = app.stems.starten(data.get("pfad"), data.get("modell", "htdemucs"))
            return self._json(202 if stand["zustand"] == "laeuft" else 200, stand)
        if self.command == "POST" and pfad == "/api/catalog/refresh":
            app.katalog.scan_im_hintergrund()
            return self._json(202, {"zustand": "laeuft"})
        if self.command == "POST" and pfad == "/api/claude/start":
            return self._json(202, app.starter.starten("Knopf auf der Seite"))
        if self.command == "POST" and pfad == "/api/ablauf":
            return self._json(200, {"schritte": ablauf.plan(data if isinstance(data, dict) else {})})
        if self.command == "POST" and pfad == "/api/mastern":
            order = app.nach.vorhanden(data)
            if lage(order)["claude_auch_dran"]:
                app.starter.starten(f"{order['id']}: vorhandener Song")
            return self._json(201, app.voll(order))
        if self.command == "POST" and pfad == "/api/explorer":
            return self._json(200, nachlauf.im_explorer(app.cfg, (data if isinstance(data, dict) else {}).get("pfad")))
        if self.command == "POST" and pfad == "/api/auftraege":
            return self._json(201, app.voll(app.nutzer.create_draft(data)))
        treffer = AUFTRAG.match(pfad)
        if treffer and self.command == "PUT" and not treffer.group(2):
            return self._json(200, app.voll(app.nutzer.update_draft(treffer.group(1), data)))
        if treffer and self.command == "POST" and treffer.group(2) in app.aktionen:
            return self._json(200, app.voll(app.aktion(treffer.group(2), treffer.group(1), data)))
        raise Ablehnung("not_found", "Diese Adresse gibt es nicht.", status=404)

    def _statisch(self, pfad):
        rel = "index.html" if pfad in ("", "/") else pfad.lstrip("/")
        ziel = (WEB / rel).resolve()
        if WEB not in ziel.parents or ziel.suffix not in TYPEN or not ziel.is_file():
            raise Ablehnung("not_found", "Diese Seite gibt es nicht.", status=404)
        body = ziel.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TYPEN[ziel.suffix])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; media-src 'self' blob:; object-src 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _bild(self, pfad):
        datei = safe_audio_path(self.app.cfg.music_root, pfad, "pfad", BILD_EXT)
        if not datei.is_file():
            raise Ablehnung("not_found", "Das Bild gibt es nicht.", "pfad", 404)
        body = datei.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", BILDER[datei.suffix.lower()])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _audio(self, pfad):
        datei = safe_audio_path(self.app.cfg.music_root, pfad)
        return self._audio_datei(datei)

    def _audio_datei(self, datei):
        if not datei.is_file():
            raise Ablehnung("not_found", "Die Datei gibt es nicht.", "pfad", 404)
        groesse = datei.stat().st_size
        start, ende, status = 0, groesse - 1, 200
        bereich = self.headers.get("Range")
        if bereich:
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", bereich.strip())
            if m and m.group(1):
                start = int(m.group(1))
                ende = min(int(m.group(2)), groesse - 1) if m.group(2) else groesse - 1
            elif m and m.group(2):
                start = max(groesse - int(m.group(2)), 0)
            if not m or not (m.group(1) or m.group(2)) or start > ende or start >= groesse:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{groesse}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            status = 206
        laenge = ende - start + 1
        self.send_response(status)
        self.send_header("Content-Type", TYPEN[datei.suffix.lower()])
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(laenge))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{ende}/{groesse}")
        self.end_headers()
        with open(datei, "rb") as fh:  # nur lesend
            fh.seek(start)
            while laenge > 0:
                block = fh.read(min(65536, laenge))
                if not block:
                    break
                self.wfile.write(block)
                laenge -= len(block)


def make_server(cfg, port=None):
    """Server anlegen (noch nicht gestartet). Jede Bind-Adresse außer 127.0.0.1 wird abgelehnt."""
    if cfg.host != LOOPBACK:
        raise Ablehnung("invalid_bind", f"Der Dienst bindet nur an {LOOPBACK}, nicht an „{cfg.host}“.", "host")
    server = ThreadingHTTPServer((LOOPBACK, cfg.port if port is None else port), Handler)
    server.daemon_threads = True
    server.app = App(cfg)
    server.app.katalog.scan_im_hintergrund()
    return server


def serve(cfg):
    server = make_server(cfg)
    print(f"Sirens läuft: http://{LOOPBACK}:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
