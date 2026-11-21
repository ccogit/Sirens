"""Revisionssichere Versionsentscheidungen für fertige Songs.

Archivieren bedeutet: Datei aus dem aktiven Musikordner in die Auftragsablage verschieben,
nicht löschen. Originale, verwendete Fassungen und Dateien anderer Aufträge sind geschützt.
"""
import shutil
from pathlib import PurePosixPath

from .contracts import Ablehnung, _text, safe_audio_path
from .service import eintrag, nur, revision
from .workflow import NUTZER, ERLEDIGT, nachlaeufe


def _geschuetzt(store, order, pfad):
    """Eine aktuelle, bei SoundCloud hinterlegte oder anderweitig referenzierte Datei bleibt stehen."""
    for fremd in store.list():
        aktuell = order if fremd["id"] == order["id"] else fremd
        if any(r["pfad"] == pfad for r in aktuell["wunsch"].get("referenzen", [])):
            return "Die Datei wird als Referenz benötigt."
        if fremd["id"] != order["id"] and any(
                pfad in t.get("dateien", []) for t in fremd.get("tracks_stand", [])):
            return "Ein anderer Auftrag verwendet diese Datei."
        for n in nachlaeufe(aktuell):
            if n["favorit"] == pfad or n["mastering"]["datei"] == pfad:
                return "Die Datei ist die aktuelle Produktionsfassung."
            if n["soundcloud"].get("stand") == "fertig" and n["soundcloud"].get("hochgeladen_datei", n["favorit"]) == pfad:
                return "Die Fassung ist noch bei SoundCloud hinterlegt."
    return ""


def archivieren(cfg, store, order, pfad):
    """Nur ausdrücklich gewählte, nicht mehr referenzierte Audiofassungen archivieren."""
    n = order.get("nachlauf")
    moeglich = {p for t in order.get("tracks_stand", []) for p in t.get("dateien", [])}
    for item in nachlaeufe(order):
        moeglich.update(e["datei"] for e in item["mastering"]["entwuerfe"])
        offen = item.get("version_entscheidung")
        if offen:
            moeglich.add(offen["alt"])
    if pfad not in moeglich:
        raise Ablehnung("invalid_path", "Diese Version gehört nicht zur Produktion.", "pfad")
    grund = _geschuetzt(store, order, pfad)
    if grund:
        raise Ablehnung("in_use", grund + " Bitte behalten oder erst den Austausch abschließen.", "pfad", 409)
    quelle = safe_audio_path(cfg.music_root, pfad, "pfad")
    if not quelle.is_file():
        raise Ablehnung("missing_file", "Die vorherige Version ist nicht mehr vorhanden.", "pfad")
    ziel = cfg.data_dir / "versionen-archiv" / order["id"] / PurePosixPath(pfad)
    if ziel.exists():
        raise Ablehnung("already_archived", "Diese Version liegt schon im Archiv.", "pfad", 409)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(quelle), str(ziel))
    for t in order.get("tracks_stand", []):
        t["dateien"] = [x for x in t.get("dateien", []) if x != pfad]
    for item in nachlaeufe(order):
        m = item["mastering"]
        m["entwuerfe"] = [e for e in m["entwuerfe"] if e["datei"] != pfad]
    return {"pfad": pfad, "archiv": str(ziel), "status": "archiviert"}


def entscheiden(service, oid, data):
    nur(data, ("revision", "entscheidung", "pfad", "bestaetigt"))
    wahl = data.get("entscheidung")
    if wahl not in ("behalten", "archivieren"):
        raise Ablehnung("invalid", "Bitte Behalten oder Archivieren wählen.", "entscheidung")
    if wahl == "archivieren" and data.get("bestaetigt") is not True:
        raise Ablehnung("confirm_required", "Das Archivieren muss bestätigt werden.", "bestaetigt", 409)

    def fn(order):
        if order["status"] not in ("nachlauf", "fertig", "abgeschlossen"):
            raise Ablehnung("invalid_transition", "Versionen erst nach der Produktion bearbeiten.", "status", 409)
        n = order.get("nachlauf")
        offen = (n or {}).get("version_entscheidung")
        pfad = data.get("pfad") or (offen or {}).get("alt")
        if not isinstance(pfad, str) or not pfad:
            raise Ablehnung("required", "Bitte die bisherige Version wählen.", "pfad")
        if wahl == "behalten":
            if not offen or pfad != offen["alt"]:
                raise Ablehnung("invalid_transition", "Für diese Version liegt keine Entscheidung vor.", "pfad", 409)
            n["version_entscheidung"] = None
            eintrag(order, NUTZER, "status", "Vorherige Master-Version bleibt erhalten.")
            return
        archiv = archivieren(service.cfg, service.store, order, pfad)
        order.setdefault("archivierte_versionen", []).append(archiv)
        if offen and offen["alt"] == pfad:
            n["version_entscheidung"] = None
        eintrag(order, NUTZER, "status", f"Version archiviert: {PurePosixPath(pfad).name}")

    return service.store.mutate(oid, revision(data), fn)


def text_aendern(service, oid, data):
    """Beschreibung neu erstellen; bestehender SoundCloud-Track wird nicht automatisch geändert."""
    nur(data, ("revision", "wunsch"))
    wunsch = _text(data.get("wunsch"), "wunsch")

    def fn(order):
        if order["status"] != "nachlauf":
            raise Ablehnung("invalid_transition", "Bitte zuerst den Song zur Bearbeitung öffnen.", "status", 409)
        n = order["nachlauf"]
        if n["soundcloud"]["stand"] == "beauftragt":
            raise Ablehnung("invalid_transition", "Bitte den laufenden Upload abwarten.", "status", 409)
        t = n["text"]
        if t["stand"] not in ERLEDIGT:
            raise Ablehnung("invalid_transition", "Eine Textänderung ist gerade nicht möglich.", "status", 409)
        t.update(stand="offen", wunsch=wunsch)
        if n["soundcloud"]["stand"] == "fertig":
            n["soundcloud"]["text_offen"] = True
        eintrag(order, NUTZER, "antwort", "Songbeschreibung und Songtext aktualisieren"
                + (f": {wunsch}" if wunsch else "."))

    return service.store.mutate(oid, revision(data), fn)
