"""Zugang für Claude: arbeitet direkt auf der Ablage, Ausgabe immer JSON."""
import dataclasses
import argparse
import json
import sys

from . import ablauf, config
from .arbeit import ClaudeAktionen
from .contracts import Ablehnung
from .store import Store
from .workflow import SCHRITTE, STATUS, lage


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Ablehnung("usage", message)


def _parser():
    p = _Parser(prog="sirens", description="Sirens: Dienst und Zugang für Claude")
    sub = p.add_subparsers(dest="befehl", required=True, parser_class=_Parser)

    def befehl(name, hilfe, mit_id=True):
        s = sub.add_parser(name, help=hilfe)
        if mit_id:
            s.add_argument("id")
        return s

    befehl("serve", "Dienst starten (nur 127.0.0.1)", False).add_argument("--port", type=int)
    befehl("todo", "alles, wofür Claude dran ist", False)
    s = befehl("list", "Aufträge auflisten", False)
    s.add_argument("--status", choices=STATUS)
    s.add_argument("--dran", choices=("nutzer", "claude", "laeuft", "niemand"))
    befehl("show", "vollständiger Auftrag")
    befehl("claim", "offen/antwort_da/fehler → in_arbeit")
    befehl("note", "Verlaufseintrag ohne Statuswechsel").add_argument("--text", required=True)
    befehl("ask", "Rückfrage stellen → rueckfrage").add_argument("--text", required=True)
    s = befehl("plan", "Plan schreiben oder ergänzen")
    s.add_argument("--file", required=True)
    s.add_argument("--wait", action="store_true", help="auf Freigabe warten → plan_wartet")
    s = befehl("track", "Fortschritt eines Songs")
    s.add_argument("--nr", type=int, required=True)
    s.add_argument("--schritt", choices=SCHRITTE, required=True)
    s.add_argument("--titel")
    s.add_argument("--file", action="append", default=[])
    s = befehl("sent", "an den Anbieter übergeben → gesendet")
    s.add_argument("--release", required=True)
    s.add_argument("--song", action="append", default=[])
    s.add_argument("--package", action="append", default=[], type=int)
    befehl("done", "Takes liegen vor → fertig")
    befehl("fail", "gescheitert → fehler").add_argument("--text", required=True)
    befehl("detail", "Arbeitsschritt melden, der jetzt beginnt").add_argument("--name", choices=ablauf.NAMEN, required=True)
    s = befehl("phase", "Ergebnis einer Nachlauf-Phase melden")
    s.add_argument("--name", choices=("ableton", "cover", "text", "soundcloud"), required=True)
    s.add_argument("--file", help="Cover-Bild bzw. Beschreibungsdatei im Musikordner")
    s.add_argument("--text", default="", help="Notiz, z. B. Name des Live-Sets")
    s.add_argument("--tag", action="append", default=[])
    s.add_argument("--link", default="")
    s.add_argument("--fehler", default="", help="Phase ist nicht gelungen: Grund")
    s.add_argument("--favorit", help="Song (Pfad des Favoriten), wenn mehrere fertig gemacht werden")
    befehl("ratings", "nicht übernommene Bewertungen")
    s = befehl("ratings-ack", "Bewertung als übernommen markieren")
    s.add_argument("--pfad", required=True)
    s.add_argument("--evaluation-id", type=int)
    befehl("catalog-ratings", "katalog-bewertungen.json ersetzen", False).add_argument("--file", required=True)
    return p


def _json_datei(pfad):
    try:
        with open(pfad, encoding="utf-8-sig") as fh:
            return json.load(fh)
    except OSError as exc:
        raise Ablehnung("file_error", f"Die Datei lässt sich nicht lesen: {exc}", "file") from None
    except ValueError as exc:
        raise Ablehnung("file_error", f"Die Datei enthält kein gültiges JSON: {exc}", "file") from None


def _ausfuehren(args, cfg):
    claude = ClaudeAktionen(cfg, Store(cfg))
    kurz = lambda order: {"id": order["id"], "status": order["status"], "revision": order["revision"],  # noqa: E731
                          **{k: v for k, v in lage(order).items() if k in ("dran", "station", "naechster_schritt")}}
    b = args.befehl
    if b == "todo":
        return {"todo": claude.todo()}
    if b == "list":
        return {"auftraege": claude.list(args.status, args.dran)}
    if b == "show":
        return claude.show(args.id)
    if b == "claim":
        return kurz(claude.claim(args.id))
    if b == "note":
        return kurz(claude.note(args.id, args.text))
    if b == "ask":
        return kurz(claude.ask(args.id, args.text))
    if b == "plan":
        return kurz(claude.set_plan(args.id, _json_datei(args.file), args.wait))
    if b == "track":
        order = claude.track(args.id, args.nr, args.schritt, args.titel, args.file)
        return {**kurz(order), "tracks_stand": order["tracks_stand"]}
    if b == "sent":
        return kurz(claude.sent(args.id, args.release, args.song, args.package))
    if b == "done":
        return kurz(claude.done(args.id))
    if b == "fail":
        return kurz(claude.fail(args.id, args.text))
    if b == "detail":
        return kurz(claude.detail(args.id, args.name))
    if b == "phase":
        order = claude.phase(args.id, args.name, args.file, args.text, args.tag, args.link, args.fehler, args.favorit)
        return {**kurz(order), "nachlauf": order["nachlauf"], "nachlauf_weitere": order.get("nachlauf_weitere", [])}
    if b == "ratings":
        return {"id": args.id, "bewertungen": claude.ratings(args.id)}
    if b == "ratings-ack":
        return kurz(claude.ratings_ack(args.id, args.pfad, args.evaluation_id))
    if b == "catalog-ratings":
        return claude.catalog_ratings(_json_datei(args.file))
    raise Ablehnung("usage", f"Unbekannter Befehl: {b}")


def main(argv=None, env=None, out=None):
    out = out or sys.stdout
    if hasattr(out, "reconfigure"):
        out.reconfigure(encoding="utf-8")
    try:
        args = _parser().parse_args(argv)
        if args.befehl == "serve" and env is None:
            config.aus_datei_setzen()  # z. B. SIRENS_STEMS_PYTHON für das Stem Studio
        cfg = config.load(env)
        if args.befehl == "serve":
            from .server import serve
            if args.port:
                cfg = dataclasses.replace(cfg, port=args.port)  # alle übrigen Einstellungen behalten
            serve(cfg)
            return 0
        result = _ausfuehren(args, cfg)
    except Ablehnung as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False), file=out)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2), file=out)
    return 0
