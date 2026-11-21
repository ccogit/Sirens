"""Aktionen des Nutzers (über die Seite). Schreibt nur Wunsch, Gespräch und Urteil."""
from .contracts import Ablehnung, _text, safe_audio_path, validate_wunsch
from .store import jetzt
from .workflow import NUTZER, station_jetzt, wechsel

VORLAGEN = {"mehr_davon": "im_stil", "nochmal_anders": "neufassung", "fortsetzung": "fortsetzung"}


def eintrag(order, von, art, text):
    neu = {"zeit": jetzt(), "von": von, "art": art, "text": text}
    if station_jetzt(order):
        neu["station"] = station_jetzt(order)
    order["verlauf"].append(neu)


def nur(data, erlaubt):
    if not isinstance(data, dict):
        raise Ablehnung("invalid", "Die Anfrage muss ein JSON-Objekt sein.")
    unbekannt = sorted(set(data) - set(erlaubt))
    if unbekannt:
        raise Ablehnung("unknown_field", f"Unbekanntes Feld: {unbekannt[0]}.", unbekannt[0])
    return data


def revision(data):
    rev = data.get("revision") if isinstance(data, dict) else None
    if isinstance(rev, bool) or not isinstance(rev, int):
        raise Ablehnung("required", "Die Revision fehlt.", "revision")
    return rev


def dateien(order):
    return [p for t in order.get("tracks_stand", []) for p in t.get("dateien", [])]


def folge_referenzen(order):
    """Favoriten, sonst die bestbewerteten Takes, sonst je Song die erste Datei."""
    alle = dateien(order)
    bew = {b["pfad"]: b for b in order.get("bewertungen", []) if b["pfad"] in alle}
    favoriten = [p for p in alle if bew.get(p, {}).get("favorit")]
    if favoriten:
        return favoriten
    if bew:
        beste = max(b["score"] for b in bew.values())
        return [p for p in alle if p in bew and bew[p]["score"] == beste]
    return [t["dateien"][0] for t in order.get("tracks_stand", []) if t.get("dateien")]


class NutzerAktionen:
    def __init__(self, cfg, store):
        self.cfg, self.store = cfg, store

    def _vorlage(self, vorgaenger_id, vorlage):
        if vorlage not in VORLAGEN:
            raise Ablehnung("invalid", f"„vorlage“ muss einer dieser Werte sein: {', '.join(VORLAGEN)}.", "vorlage")
        alt = self.store.load(vorgaenger_id) if isinstance(vorgaenger_id, str) else None
        if alt is None or alt["status"] not in ("fertig", "abgeschlossen", "nachlauf"):
            raise Ablehnung("invalid", "Ein Folgeauftrag braucht einen fertigen Auftrag als Vorgänger.",
                            "vorgaenger_id", 409)
        refs = []
        for pfad in folge_referenzen(alt)[:12]:
            try:
                if safe_audio_path(self.cfg.music_root, pfad).is_file():
                    refs.append({"pfad": pfad, "gewicht": "stark" if vorlage == "mehr_davon" else "normal"})
            except Ablehnung:
                continue
        w = alt["wunsch"]
        optionen = {k: v for k, v in w["optionen"].items() if k != "titelwunsch"}
        return {"weg": "referenz", "umfang": w["umfang"], "track_count": w["track_count"],
                "artist_slug": w["artist_slug"], "bezug": VORLAGEN[vorlage], "referenzen": refs,
                "wunsch": w["wunsch"] if vorlage == "nochmal_anders" else "", "optionen": optionen}

    def create_draft(self, data):
        data = dict(data) if isinstance(data, dict) else data
        vorgaenger_id = vorlage = None
        if isinstance(data, dict):
            vorgaenger_id, vorlage = data.pop("vorgaenger_id", None), data.pop("vorlage", None)
            data.pop("revision", None)
        if vorgaenger_id is not None or vorlage is not None:
            data = {**self._vorlage(vorgaenger_id, vorlage), **data}
        wunsch = validate_wunsch(data, self.cfg.music_root, vollstaendig=False)
        return self.store.create(wunsch, vorgaenger_id)

    def update_draft(self, oid, data):
        rev = revision(data)
        data = {k: v for k, v in data.items() if k != "revision"}
        wunsch = validate_wunsch(data, self.cfg.music_root, vollstaendig=False)

        def fn(order):
            if order["status"] != "entwurf":
                raise Ablehnung("not_editable", "Der Auftrag ist abgeschickt und kann nicht mehr geändert werden.",
                                "status", 409)
            order["wunsch"] = wunsch
        return self.store.mutate(oid, rev, fn)

    def submit(self, oid, data):
        nur(data, ("revision",))

        def fn(order):
            wechsel(order, "offen", NUTZER)
            order["wunsch"] = validate_wunsch(order["wunsch"], self.cfg.music_root, vollstaendig=True)
            eintrag(order, NUTZER, "status", "Auftrag abgeschickt.")
        return self.store.mutate(oid, revision(data), fn)

    def answer(self, oid, data):
        nur(data, ("revision", "text"))
        text = _text(data.get("text"), "text", pflicht=True)

        def fn(order):
            if order["status"] != "rueckfrage":
                raise Ablehnung("invalid_transition", "Zu diesem Auftrag ist gerade keine Frage offen.", "status", 409)
            wechsel(order, "antwort_da", NUTZER)
            eintrag(order, NUTZER, "antwort", text)
        return self.store.mutate(oid, revision(data), fn)

    def plan_decision(self, oid, data):
        nur(data, ("revision", "entscheidung", "text", "tracks"))
        entscheidung = data.get("entscheidung")
        if entscheidung not in ("freigeben", "aendern"):
            raise Ablehnung("invalid", "„entscheidung“ muss „freigeben“ oder „aendern“ sein.", "entscheidung")
        zeilen = []
        if entscheidung == "aendern":
            allgemein = _text(data.get("text"), "text")
            if allgemein:
                zeilen.append(allgemein)
            tracks = data.get("tracks") or []
            if not isinstance(tracks, list):
                raise Ablehnung("invalid", "„tracks“ muss eine Liste sein.", "tracks")
            for i, t in enumerate(tracks):
                feld = f"tracks[{i}]"
                nr = nur(t, ("nr", "text")).get("nr")
                if isinstance(nr, bool) or not isinstance(nr, int) or not 1 <= nr <= 20:
                    raise Ablehnung("invalid", "„nr“ muss eine Zahl von 1 bis 20 sein.", feld)
                text = _text(t.get("text"), feld + ".text")
                if text:
                    zeilen.append(f"Song {nr}: {text}")
            if not zeilen:
                raise Ablehnung("required", "Bitte schreiben, was am Plan anders sein soll.", "text")

        def fn(order):
            if order["status"] != "plan_wartet":
                raise Ablehnung("invalid_transition", "Zu diesem Auftrag wartet gerade kein Plan.", "status", 409)
            wechsel(order, "antwort_da", NUTZER)
            if entscheidung == "freigeben":
                eintrag(order, NUTZER, "antwort", "Plan freigegeben.")
            else:
                eintrag(order, NUTZER, "plan_aenderung", "\n".join(zeilen))
        return self.store.mutate(oid, revision(data), fn)

    def rate(self, oid, data):
        nur(data, ("revision", "pfad", "score", "favorit", "kommentar"))
        score, favorit = data.get("score"), data.get("favorit", False)
        if isinstance(score, bool) or not isinstance(score, int) or not -2 <= score <= 2:
            raise Ablehnung("invalid", "Die Bewertung muss eine ganze Zahl von −2 bis +2 sein.", "score")
        if not isinstance(favorit, bool):
            raise Ablehnung("invalid", "„favorit“ muss wahr oder falsch sein.", "favorit")
        kommentar = _text(data.get("kommentar"), "kommentar")
        pfad = data.get("pfad")

        def fn(order):
            if order["status"] not in ("fertig", "abgeschlossen", "nachlauf"):
                raise Ablehnung("invalid_transition", "Bewerten geht erst, wenn die Songs fertig sind.", "status", 409)
            track = next((t for t in order["tracks_stand"] if pfad in t.get("dateien", [])), None)
            if track is None:
                raise Ablehnung("invalid_path", "Diese Datei gehört nicht zu diesem Auftrag.", "pfad")
            neu = {"pfad": pfad, "score": score, "favorit": favorit, "kommentar": kommentar}
            alt = next((b for b in order["bewertungen"] if b["pfad"] == pfad), None)
            if alt is None:
                order["bewertungen"].append({**neu, "zeit": jetzt(), "uebernommen": False})
            elif any(alt.get(k) != v for k, v in neu.items()):
                alt.pop("evaluation_id", None)
                alt.update(neu, zeit=jetzt(), uebernommen=False)
            if favorit:  # je Song höchstens ein Favorit
                for b in order["bewertungen"]:
                    if b["pfad"] != pfad and b["pfad"] in track["dateien"] and b["favorit"]:
                        b.update(favorit=False, zeit=jetzt(), uebernommen=False)
        return self.store.mutate(oid, revision(data), fn)

    def close(self, oid, data):
        nur(data, ("revision",))

        def fn(order):
            wechsel(order, "abgeschlossen", NUTZER)
            eintrag(order, NUTZER, "status", "Auftrag abgeschlossen.")
        return self.store.mutate(oid, revision(data), fn)

    def cancel(self, oid, data):
        nur(data, ("revision",))

        def fn(order):
            wechsel(order, "abgebrochen", NUTZER)
            eintrag(order, NUTZER, "status", "Auftrag abgebrochen.")
        return self.store.mutate(oid, revision(data), fn)
