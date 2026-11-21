"""Aktionen von Claude (über die CLI). Schreibt Arbeitsstand, Gespräch und `uebernommen`."""
from pathlib import Path

from . import ablauf, nachlauf
from .contracts import AUDIO_EXT, Ablehnung, _text, safe_audio_path
from .service import eintrag, nur
from .store import write_json_atomic
from .workflow import CLAUDE, SCHRITTE, claude_phasen, lage, nachlaeufe, offene_bewertungen, wechsel

PLAN_TRACK = ("titel", "idee", "stil_kurz", "text")
GRUND = {"offen": "Neuer Auftrag", "fehler": "Nach einem Fehler erneut aufnehmen"}


def _nr(value, feld):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 20:
        raise Ablehnung("invalid", "„nr“ muss eine Zahl von 1 bis 20 sein.", feld)
    return value


def _stand(order, nr):
    stand = next((t for t in order["tracks_stand"] if t["nr"] == nr), None)
    if stand is None:
        stand = {"nr": nr, "titel": "", "schritt": "geplant", "dateien": []}
        order["tracks_stand"].append(stand)
        order["tracks_stand"].sort(key=lambda t: t["nr"])
    return stand


def _plan_einarbeiten(order, neu):
    nur(neu, ("titel", "konzept", "tracks"))
    plan = order["plan"] or {"titel": "", "konzept": "", "tracks": []}
    for feld in ("titel", "konzept"):
        if feld in neu:
            plan[feld] = _text(neu[feld], f"plan.{feld}")
    tracks = neu.get("tracks", [])
    if not isinstance(tracks, list):
        raise Ablehnung("invalid", "„tracks“ muss eine Liste sein.", "plan.tracks")
    for i, t in enumerate(tracks):
        feld = f"plan.tracks[{i}]"
        nr = _nr(nur(t, ("nr",) + PLAN_TRACK).get("nr"), feld)
        ziel = next((p for p in plan["tracks"] if p["nr"] == nr), None)
        if ziel is None:
            ziel = {"nr": nr, **{k: "" for k in PLAN_TRACK}}
            plan["tracks"].append(ziel)
        for k in PLAN_TRACK:
            if k in t:
                ziel[k] = _text(t[k], f"{feld}.{k}")
        stand = _stand(order, nr)
        stand["titel"] = ziel["titel"] or stand["titel"]
    plan["tracks"].sort(key=lambda t: t["nr"])
    order["plan"] = plan


class ClaudeAktionen:
    def __init__(self, cfg, store):
        self.cfg, self.store = cfg, store

    def _aendern(self, oid, fn):
        return self.store.mutate(oid, None, fn)

    def _relativ(self, pfad, endungen=AUDIO_EXT):
        """Datei im Musikordner; absolute Pfade darunter werden relativ gemacht."""
        if isinstance(pfad, str) and Path(pfad).is_absolute():
            try:
                pfad = Path(pfad).resolve().relative_to(self.cfg.music_root.resolve()).as_posix()
            except ValueError:
                raise Ablehnung("invalid_path", "Die Datei liegt nicht im Musikordner.", "file") from None
        if not safe_audio_path(self.cfg.music_root, pfad, "file", endungen).is_file():
            raise Ablehnung("missing_file", f"Die Datei gibt es nicht: {pfad}", "file")
        return pfad.strip()

    def todo(self):
        result = []
        for order in reversed(self.store.list()):
            stand = lage(order)
            if not stand["claude_auch_dran"]:
                continue
            gruende = []
            if order["status"] in GRUND:
                gruende.append(GRUND[order["status"]])
            nutzer = [e for e in order["verlauf"] if e["von"] == "nutzer"]
            if order["status"] == "antwort_da" and nutzer:
                letzte = nutzer[-1]
                gruende.append({"plan_aenderung": "Planänderung gewünscht"}.get(letzte["art"], letzte["text"]
                               if letzte["text"] == "Plan freigegeben." else "Antwort auf die Rückfrage"))
            if order["status"] in ("nachlauf", "fertig"):
                alle = nachlaeufe(order)  # bei mehreren Songs steht der Favorit dabei (für `phase --favorit`)
                gruende += [f"Nachlauf: {name}" + (f" [{n['favorit']}]" if len(alle) > 1 else "")
                            for n in alle for name in claude_phasen(n)]
            if stand["offene_bewertungen"]:
                gruende.append(f"{stand['offene_bewertungen']} Bewertung(en) übernehmen")
            result.append({"id": order["id"], "status": order["status"], "gruende": gruende,
                           "umfang": order["wunsch"]["umfang"], "weg": order["wunsch"]["weg"],
                           "letzte_nutzernachricht": nutzer[-1]["text"] if nutzer else ""})
        return result

    def list(self, status=None, dran=None):
        result = []
        for order in self.store.list():
            stand = lage(order)
            if (status and order["status"] != status) or (dran and stand["dran"] != dran):
                continue
            result.append({"id": order["id"], "status": order["status"], "dran": stand["dran"],
                           "station": stand["station"], "naechster_schritt": stand["naechster_schritt"],
                           "updated_at": order["updated_at"]})
        return result

    def show(self, oid):
        order = self.store.load(oid)
        for ref in order["wunsch"]["referenzen"]:
            datei = self.cfg.music_root.joinpath(*ref["pfad"].split("/"))
            ref["absolut"], ref["existiert"] = str(datei), datei.is_file()
        order["lage"] = lage(order)
        zusatz = nachlauf.info(self.cfg, order)
        if zusatz:
            absolut = lambda n: str(self.cfg.music_root.joinpath(*nachlauf.endfassung(n).split("/")))  # noqa: E731
            order["nachlauf_info"] = {**zusatz, "endfassung_absolut": absolut(order["nachlauf"]),
                                      "endfassungen": {n["favorit"]: absolut(n) for n in nachlaeufe(order)}}
        return order

    def claim(self, oid):
        def fn(order):
            wechsel(order, "in_arbeit", CLAUDE)
            eintrag(order, CLAUDE, "status", "Claude hat den Auftrag übernommen.")
        return self._aendern(oid, fn)

    def note(self, oid, text):
        text = _text(text, "text", pflicht=True)
        return self._aendern(oid, lambda order: eintrag(order, CLAUDE, "notiz", text))

    def ask(self, oid, text):
        text = _text(text, "text", pflicht=True)

        def fn(order):
            wechsel(order, "rueckfrage", CLAUDE)
            eintrag(order, CLAUDE, "rueckfrage", text)
        return self._aendern(oid, fn)

    def set_plan(self, oid, plan, wait=False):
        def fn(order):
            if order["status"] != "in_arbeit":
                raise Ablehnung("invalid_transition", "Der Plan lässt sich nur im Status „in_arbeit“ schreiben.",
                                "status", 409)
            _plan_einarbeiten(order, plan)
            if wait:
                wechsel(order, "plan_wartet", CLAUDE)
                eintrag(order, CLAUDE, "status", "Der Plan liegt zur Freigabe vor.")
        return self._aendern(oid, fn)

    def track(self, oid, nr, schritt, titel=None, files=()):
        if schritt not in SCHRITTE:
            raise Ablehnung("invalid", f"„schritt“ muss einer dieser Werte sein: {', '.join(SCHRITTE)}.", "schritt")
        neu = [self._relativ(p) for p in files]

        def fn(order):
            if order["status"] not in ("in_arbeit", "gesendet", "fertig"):
                raise Ablehnung("invalid_transition", "Fortschritt lässt sich in diesem Status nicht melden.",
                                "status", 409)
            stand = _stand(order, _nr(nr, "nr"))
            stand["schritt"] = schritt
            if titel:
                stand["titel"] = _text(titel, "titel")
            stand["dateien"] += [p for p in neu if p not in stand["dateien"]]
        return self._aendern(oid, fn)

    def sent(self, oid, release, songs=(), packages=()):
        release = _text(release, "release", pflicht=True)

        def fn(order):
            wechsel(order, "gesendet", CLAUDE)
            order["ergebnis"] = {"release_slug": release, "song_slugs": list(songs), "package_ids": list(packages)}
            eintrag(order, CLAUDE, "status", "Die Songs sind zur Erzeugung übergeben.")
        return self._aendern(oid, fn)

    def done(self, oid):
        def fn(order):
            if not any(t.get("dateien") for t in order["tracks_stand"]):
                raise Ablehnung("no_files", "Fertig melden geht erst mit mindestens einer Datei.", "tracks_stand", 409)
            wechsel(order, "fertig", CLAUDE)
            eintrag(order, CLAUDE, "status", "Die Songs sind fertig und können angehört werden.")
        return self._aendern(oid, fn)

    def fail(self, oid, text):
        text = _text(text, "text", pflicht=True)

        def fn(order):
            wechsel(order, "fehler", CLAUDE)
            eintrag(order, CLAUDE, "status", f"Fehler: {text}")
        return self._aendern(oid, fn)

    def detail(self, oid, name):
        """Melden, welcher Arbeitsschritt jetzt beginnt (Anzeige „Ablauf im Detail“)."""
        if name not in ablauf.NAMEN:
            raise Ablehnung("invalid", f"„name“ muss einer dieser Werte sein: {', '.join(ablauf.NAMEN)}.", "name")

        def fn(order):
            if order["status"] != "in_arbeit":
                raise Ablehnung("invalid_transition", "Der Schritt lässt sich nur im Status „in_arbeit“ melden.",
                                "status", 409)
            order["detail_schritt"] = name
        return self._aendern(oid, fn)

    def phase(self, oid, name, file=None, text="", tags=(), link="", fehler="", favorit=None):
        """Ergebnis einer Nachlauf-Phase melden (ableton, cover, text, soundcloud); `favorit` nennt den Song."""
        pfad = None
        if name in nachlauf.ENDUNGEN and not fehler:
            pfad = self._relativ(file, nachlauf.ENDUNGEN[name])
        text, fehler = _text(text, "text"), _text(fehler, "fehler")
        return self._aendern(oid, lambda order: nachlauf.phase_melden(
            self.cfg, order, name, pfad, text, tags, link or "", fehler, favorit))

    def ratings(self, oid):
        return offene_bewertungen(self.store.load(oid))

    def ratings_ack(self, oid, pfad, evaluation_id=None):
        def fn(order):
            bewertung = next((b for b in order["bewertungen"] if b["pfad"] == pfad), None)
            if bewertung is None:
                raise Ablehnung("not_found", "Zu dieser Datei gibt es keine Bewertung.", "pfad", 404)
            bewertung["uebernommen"] = True
            if evaluation_id is not None:
                bewertung["evaluation_id"] = evaluation_id
        return self._aendern(oid, fn)

    def catalog_ratings(self, data):
        if not isinstance(data, dict):
            raise Ablehnung("invalid", "Erwartet wird ein Objekt {pfad: {score, label}}.", "file")
        sauber = {}
        for pfad, wert in data.items():
            score = nur(wert, ("score", "label")).get("score")
            if isinstance(score, bool) or not isinstance(score, int) or not -2 <= score <= 2:
                raise Ablehnung("invalid", f"Ungültige Bewertung für {pfad}.", "score")
            sauber[pfad] = {"score": score, "label": _text(wert.get("label"), "label")}
        self.cfg.data_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(self.cfg.catalog_ratings_file, sauber)
        return {"anzahl": len(sauber), "datei": str(self.cfg.catalog_ratings_file)}
