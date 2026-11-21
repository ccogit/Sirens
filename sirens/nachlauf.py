"""Nachlauf für den Favoriten: Mastering, Ableton, Cover, Songbeschreibung, SoundCloud.

Der Nutzer entscheidet auf der Seite; Claude meldet Ergebnisse über die CLI (`phase`).
Nichts hier überschreibt oder löscht eine Datei im Musikordner.
"""
import json
import os
import subprocess
from pathlib import PurePosixPath

from . import versionen

from . import analyse, soundcloud as sc, studio
from .contracts import AUDIO_EXT, BILD_EXT, TEXT_EXT, Ablehnung, _text, parse_pfad, safe_audio_path, validate_wunsch
from .service import dateien, eintrag, nur, revision
from .workflow import CLAUDE, ERLEDIGT, NUTZER, PHASEN, nachlaeufe, wechsel

MAX_COVER = 5  # höchstens fünf Bild-Erzeugungen je Song (Nutzer, 21.11.2026)
ENDUNGEN = {"cover": BILD_EXT, "text": TEXT_EXT}


def neu(favorit):
    return {"favorit": favorit,
            "mastering": {"stand": "offen", "weg": "", "datei": "", "entwuerfe": [], "analyse": None},
            "ableton": {"stand": "offen", "notiz": ""},
            "cover": {"stand": "offen", "datei": "", "versuche": 0, "wunsch": "", "fehler": ""},
            "text": {"stand": "offen", "datei": "", "beschreibung": "", "tags": []},
            "soundcloud": {"stand": "offen", "sichtbarkeit": "privat", "promotion": False, "link": "", "fehler": "",
                           "cover_offen": False, "cover_fehler": "", "text_offen": False, "audio_offen": False}}


def im_explorer(cfg, pfad):
    """Datei im Windows-Explorer zeigen (markiert im Ordner). Nur Dateien im Musikordner."""
    datei = safe_audio_path(cfg.music_root, pfad, "pfad", AUDIO_EXT + BILD_EXT + TEXT_EXT)
    if not datei.is_file():
        raise Ablehnung("not_found", "Die Datei gibt es nicht.", "pfad", 404)
    eigen = os.environ.get("SIRENS_EXPLORER_CMD")
    try:
        subprocess.Popen([*json.loads(eigen), str(datei)] if eigen else f'explorer.exe /select,"{datei}"')
    except (OSError, ValueError) as exc:
        raise Ablehnung("no_explorer", f"Der Explorer ließ sich nicht öffnen: {exc}", status=500) from None
    return {"gezeigt": str(datei)}


def endfassung(n):
    """Die Datei, mit der weitergearbeitet wird: der gewählte Master, sonst der Favorit."""
    return n["mastering"]["datei"] or n["favorit"]


def kandidaten(cfg, n):
    """Eigene Master-Dateien, die im Ordner des Favoriten (und eine Ebene darunter) liegen."""
    favorit = n["favorit"]
    ordner = cfg.music_root.joinpath(*PurePosixPath(favorit).parts[:-1])
    titel = parse_pfad(favorit)["titel"].lower()
    eigene = {e["datei"] for e in n["mastering"]["entwuerfe"]}
    treffer = []
    for muster in ("*", "*/*"):
        for datei in ordner.glob(muster):
            name = datei.name.lower()
            if datei.is_file() and datei.suffix.lower() in AUDIO_EXT and "master" in name and titel in name:
                rel = datei.relative_to(cfg.music_root).as_posix()
                if rel != favorit and rel not in eigene:
                    treffer.append(rel)
    return sorted(treffer)


def cover_kandidaten(cfg, n):
    """Andere Bilder zum Song im Ordner des Favoriten (und eine Ebene darunter): frühere Cover und eigene Bilder."""
    ordner = cfg.music_root.joinpath(*PurePosixPath(n["favorit"]).parts[:-1])
    titel = parse_pfad(n["favorit"])["titel"].lower()
    treffer = {d.relative_to(cfg.music_root).as_posix() for muster in ("*", "*/*") for d in ordner.glob(muster)
               if d.is_file() and d.suffix.lower() in BILD_EXT and titel in d.name.lower()}
    return sorted(treffer - {n["cover"]["datei"]})


def info(cfg, order):
    """Zusatzangaben für die Seite (nicht gespeichert)."""
    n = order.get("nachlauf")
    if not n:
        return None
    return {"kandidaten": kandidaten(cfg, n), "endfassung": endfassung(n), "cover_kandidaten": cover_kandidaten(cfg, n),
            "max_cover": MAX_COVER, "werkzeuge": {**studio.werkzeuge(cfg), "soundcloud": sc.bereit()},
            "favorit_absolut": str(cfg.music_root.joinpath(*n["favorit"].split("/"))),
            "standard": studio.STANDARD, "grenzen": studio.GRENZEN}


def _im_nachlauf(order):
    if order["status"] != "nachlauf":
        raise Ablehnung("invalid_transition", "Das geht erst, wenn der Favorit fertig gemacht wird.", "status", 409)
    return order["nachlauf"]


class NachlaufAktionen:
    """Entscheidungen des Nutzers im Nachlauf."""

    def __init__(self, cfg, store):
        self.cfg, self.store = cfg, store

    def vorhanden(self, data):
        """Einen vorhandenen Song ohne Songauftrag fertig machen: Auftrag, der direkt im Nachlauf beginnt.

        `schritte` nennt die gewünschten Phasen (Standard: nur Mastering); alle anderen gelten als ausgelassen.
        Der Export nach Ableton ist immer auf Knopfdruck möglich.
        """
        pfad = nur(data, ("pfad", "schritte")).get("pfad")
        schritte = data.get("schritte", ["mastering"])
        if not isinstance(schritte, list) or set(schritte) - set(PHASEN):
            raise Ablehnung("invalid", f"„schritte“ darf nur enthalten: {', '.join(PHASEN)}.", "schritte")
        if not safe_audio_path(self.cfg.music_root, pfad).is_file():
            raise Ablehnung("missing_file", "Die Datei gibt es nicht.", "pfad")
        pfad = pfad.strip()
        teile = parse_pfad(pfad)
        wunsch = validate_wunsch({"weg": "referenz", "artist_slug": teile["artist_slug"], "referenzen": [{"pfad": pfad}],
                                  "optionen": {"titelwunsch": f"Fertig machen: {teile['titel']}"}},
                                 self.cfg.music_root, vollstaendig=False)
        order = self.store.create(wunsch)

        def fn(order):
            order["status"] = "nachlauf"
            order["tracks_stand"] = [{"nr": 1, "titel": teile["titel"], "schritt": "fertig", "dateien": [pfad]}]
            n = neu(pfad)
            n["vorhanden"] = True
            for name in PHASEN:
                if name not in schritte:
                    n[name]["stand"] = "ausgelassen"
            order["nachlauf"] = n
            eintrag(order, NUTZER, "status", f"Vorhandenen Song fertig machen: {PurePosixPath(pfad).name}")
        return self.store.mutate(order["id"], None, fn)

    def start(self, oid, data):
        nur(data, ("revision", "pfad"))
        pfad = data.get("pfad")

        def fn(order):
            if pfad not in dateien(order):
                raise Ablehnung("invalid_path", "Diese Datei gehört nicht zu diesem Auftrag.", "pfad")
            if order["status"] != "nachlauf":  # im Nachlauf wechselt der Aufruf nur den Song
                wechsel(order, "nachlauf", NUTZER)
            aktiv = order.get("nachlauf")
            if not aktiv or aktiv["favorit"] != pfad:
                # Der bisherige Song wird zurückgestellt, nicht verworfen; ein schon begonnener kommt zurück.
                weitere = order.setdefault("nachlauf_weitere", [])
                if aktiv:
                    weitere.append(aktiv)
                gemerkt = next((n for n in weitere if n["favorit"] == pfad), None)
                if gemerkt:
                    weitere.remove(gemerkt)
                order["nachlauf"] = gemerkt or neu(pfad)
            eintrag(order, NUTZER, "status", f"Favorit wird fertig gemacht: {PurePosixPath(pfad).name}")
        return self.store.mutate(oid, revision(data), fn)

    def anhoeren(self, oid, data):
        """Zurück zum Anhören, um weitere Songs zu bewerten und fertig zu machen. Der Stand jedes Songs bleibt."""
        nur(data, ("revision",))

        def fn(order):
            n = _im_nachlauf(order)
            if n.get("vorhanden") or n.get("nur_mastern"):
                raise Ablehnung("invalid_transition", "Dieser Auftrag hat keine Songs zum Anhören.", "status", 409)
            wechsel(order, "fertig", NUTZER)
            eintrag(order, NUTZER, "status", "Zurück zum Anhören.")
        return self.store.mutate(oid, revision(data), fn)

    def analyse(self, oid, data):
        """Favorit vermessen; das Ergebnis (Messwerte, Empfehlungen, Voreinstellungen) steht danach im Auftrag."""
        nur(data, ("revision",))
        order = self.store.load(oid)
        n = _im_nachlauf(order)
        plan = order.get("plan") or {}
        tags = [t.get("stil_kurz", "") for t in plan.get("tracks", [])] + [plan.get("titel", ""),
                                                                           order["wunsch"]["wunsch"]]
        ergebnis = analyse.analysieren(self.cfg, n["favorit"], [t for t in tags if t])

        def fn(order):
            _im_nachlauf(order)["mastering"]["analyse"] = ergebnis
        return self.store.mutate(oid, None, fn)

    def studio(self, oid, data):
        """Studio-Master rendern (ffmpeg) oder an eine Referenz angleichen (Matchering). Wird nur ein Entwurf."""
        nur(data, ("revision", "einstellungen", "referenz", "automatik"))
        rev = revision(data)
        order = self.store.load(oid)
        n = _im_nachlauf(order)
        if rev != order["revision"]:
            raise Ablehnung("revision_conflict", "Der Auftrag wurde inzwischen geändert. Bitte erneut versuchen.",
                            "revision", 409)
        if data.get("automatik") is not None:
            entwurf = studio.automatik(self.cfg, n["favorit"], data["automatik"])
        elif data.get("referenz"):
            entwurf = studio.angleichen(self.cfg, n["favorit"], data["referenz"])
        else:
            entwurf = studio.rendern(self.cfg, n["favorit"], data.get("einstellungen"))

        def fn(order):
            _im_nachlauf(order)["mastering"]["entwuerfe"].append(entwurf)
        return self.store.mutate(oid, None, fn)

    def master(self, oid, data):
        nur(data, ("revision", "weg", "datei"))
        weg, datei = data.get("weg"), data.get("datei")
        if weg not in ("datei", "ohne"):
            raise Ablehnung("invalid", "„weg“ muss „datei“ oder „ohne“ sein.", "weg")
        if weg == "datei" and not safe_audio_path(self.cfg.music_root, datei, "datei").is_file():
            raise Ablehnung("missing_file", "Die Master-Datei gibt es nicht.", "datei")

        def fn(order):
            n = _im_nachlauf(order)
            if n["soundcloud"]["stand"] == "beauftragt":
                raise Ablehnung("invalid_transition", "Der SoundCloud-Upload läuft. Bitte danach ändern.", "status", 409)
            m = n["mastering"]
            vorher = m["datei"]
            if weg == "ohne":
                m.update(stand="ausgelassen", weg="ohne", datei="")
                n["version_entscheidung"] = {"alt": vorher, "neu": n["favorit"]} if vorher else None
                if n["soundcloud"]["stand"] == "fertig":
                    n["soundcloud"]["audio_offen"] = endfassung(n) != n["soundcloud"].get("hochgeladen_datei", n["favorit"])
                eintrag(order, NUTZER, "status", "Ohne Mastering weiter.")
                return
            eigen = next((e for e in m["entwuerfe"] if e["datei"] == datei), None)
            if eigen is None and datei not in kandidaten(self.cfg, n):
                raise Ablehnung("invalid_path", "Diese Datei ist kein Master zu diesem Song.", "datei")
            m.update(stand="fertig", weg=eigen["weg"] if eigen else "eigene Datei", datei=datei)
            n["version_entscheidung"] = {"alt": vorher, "neu": datei} if vorher and vorher != datei else None
            if n["soundcloud"]["stand"] == "fertig":
                n["soundcloud"]["audio_offen"] = endfassung(n) != n["soundcloud"].get("hochgeladen_datei", n["favorit"])
            eintrag(order, NUTZER, "status", f"Master gewählt: {PurePosixPath(datei).name}")
        return self.store.mutate(oid, revision(data), fn)

    def version(self, oid, data):
        return versionen.entscheiden(self, oid, data)

    def text_aendern(self, oid, data):
        return versionen.text_aendern(self, oid, data)

    def ableton(self, oid, data):
        nur(data, ("revision",))

        def fn(order):
            a = _im_nachlauf(order)["ableton"]
            a.update(stand="beauftragt", notiz="")
            eintrag(order, NUTZER, "status", "Bitte nach Ableton exportieren.")
        return self.store.mutate(oid, revision(data), fn)

    def cover(self, oid, data):
        """annehmen, neu (statt des vorliegenden), ohne; später: aendern (neues von Claude) oder datei (anderes Bild wählen)."""
        nur(data, ("revision", "entscheidung", "text", "datei"))
        wahl, datei = data.get("entscheidung"), data.get("datei")
        if wahl not in ("annehmen", "neu", "ohne", "aendern", "datei"):
            raise Ablehnung("invalid", "„entscheidung“ muss annehmen, neu, ohne, aendern oder datei sein.", "entscheidung")
        wunsch = _text(data.get("text"), "text")

        def fn(order):
            n = _im_nachlauf(order)
            c, s = n["cover"], n["soundcloud"]
            oben = s["stand"] == "fertig"  # der Song liegt schon bei SoundCloud: ein anderes Cover muss dort ersetzt werden
            if s["stand"] == "beauftragt":
                raise Ablehnung("invalid_transition", "Der Song wird gerade hochgeladen. Danach lässt sich das Cover ändern.",
                                "status", 409)
            if wahl == "datei":
                if datei not in cover_kandidaten(self.cfg, n):
                    raise Ablehnung("invalid_path", "Dieses Bild gehört nicht zu diesem Song.", "datei")
                c.update(stand="fertig", datei=datei, fehler="")
                s["cover_offen"] = oben
                eintrag(order, NUTZER, "status", f"Cover gewählt: {PurePosixPath(datei).name}")
            elif wahl == "ohne":
                if oben:
                    raise Ablehnung("invalid_transition", "Der Song liegt schon mit Cover bei SoundCloud.", "status", 409)
                c.update(stand="ausgelassen")
                eintrag(order, NUTZER, "status", "Ohne Cover weiter.")
            elif wahl in ("neu", "aendern"):
                if c["stand"] not in (("wartet",) if wahl == "neu" else ERLEDIGT):
                    raise Ablehnung("invalid_transition", "Ein neues Cover lässt sich gerade nicht anfordern.", "status", 409)
                if c["versuche"] >= MAX_COVER:
                    raise Ablehnung("limit", f"Mehr als {MAX_COVER} Cover je Song sind nicht vorgesehen.",
                                    "entscheidung", 409)
                c.update(stand="offen", wunsch=wunsch, fehler="")
                eintrag(order, NUTZER, "antwort", "Bitte ein neues Cover" + (f": {wunsch}" if wunsch else "."))
            elif c["stand"] != "wartet":
                raise Ablehnung("invalid_transition", "Es liegt gerade kein Cover zur Entscheidung vor.", "status", 409)
            else:
                if not c["datei"]:
                    raise Ablehnung("invalid", "Es gibt noch kein Cover zum Annehmen.", "entscheidung", 409)
                c.update(stand="fertig")
                s["cover_offen"] = oben
                eintrag(order, NUTZER, "antwort", "Cover angenommen.")
        return self.store.mutate(oid, revision(data), fn)

    def _cover_ersetzen(self, oid, rev):
        """Das angenommene Cover bei SoundCloud einsetzen (der Song liegt dort schon). Ergebnis steht danach im Auftrag."""
        order = self.store.load(oid)
        n = _im_nachlauf(order)
        if rev != order["revision"]:
            raise Ablehnung("revision_conflict", "Der Auftrag wurde inzwischen geändert. Bitte erneut versuchen.",
                            "revision", 409)
        if n["soundcloud"]["stand"] != "fertig" or n["cover"]["stand"] != "fertig" or not n["cover"]["datei"]:
            raise Ablehnung("invalid_transition", "Dafür muss der Song bei SoundCloud liegen und ein Cover gewählt sein.",
                            "status", 409)
        favorit, fehler = n["favorit"], sc.cover_ersetzen(self.cfg, n["soundcloud"]["link"], n["cover"]["datei"])

        def fn(order):
            s = next(x for x in nachlaeufe(order) if x["favorit"] == favorit)["soundcloud"]
            s.update(cover_offen=bool(fehler), cover_fehler=fehler)
            if not fehler:
                eintrag(order, NUTZER, "status", "Cover bei SoundCloud ersetzt.")
        return self.store.mutate(oid, None, fn)

    def soundcloud(self, oid, data):
        nur(data, ("revision", "entscheidung", "sichtbarkeit", "promotion", "bestaetigt"))
        wahl, sicht, promo = data.get("entscheidung"), data.get("sichtbarkeit", "privat"), data.get("promotion", False)
        if wahl == "cover":
            return self._cover_ersetzen(oid, revision(data))
        if wahl == "metadaten":
            if data.get("bestaetigt") is not True:
                raise Ablehnung("confirm_required", "SoundCloud-Änderungen bitte bestätigen.", "bestaetigt", 409)
            order = self.store.load(oid)
            n = _im_nachlauf(order)
            if revision(data) != order["revision"]:
                raise Ablehnung("revision_conflict", "Der Auftrag wurde inzwischen geändert.", "revision", 409)
            if n["soundcloud"]["stand"] != "fertig" or n["text"]["stand"] != "fertig":
                raise Ablehnung("invalid_transition", "Für SoundCloud muss die neue Beschreibung fertig sein.", "status", 409)
            fehler = sc.metadaten_ersetzen(n["soundcloud"]["link"], n["text"]["beschreibung"], n["text"]["tags"])
            def fn(order):
                aktu = _im_nachlauf(order)["soundcloud"]
                aktu.update(text_offen=bool(fehler), text_fehler=fehler)
                if not fehler:
                    eintrag(order, NUTZER, "status", "Beschreibung auf dem bestehenden SoundCloud-Track aktualisiert.")
            return self.store.mutate(oid, None, fn)
        if wahl == "audio_bestaetigt":
            if data.get("bestaetigt") is not True:
                raise Ablehnung("confirm_required", "Bitte den manuellen Austausch auf SoundCloud bestätigen.", "bestaetigt", 409)
            def fn(order):
                n = _im_nachlauf(order)
                if n["soundcloud"]["stand"] != "fertig" or not n["soundcloud"].get("audio_offen"):
                    raise Ablehnung("invalid_transition", "Keine ausstehende Audio-Aktualisierung.", "status", 409)
                n["soundcloud"].update(audio_offen=False, hochgeladen_datei=endfassung(n))
                eintrag(order, NUTZER, "status", "Audio-Austausch auf SoundCloud vom Nutzer bestätigt.")
            return self.store.mutate(oid, revision(data), fn)
        if wahl not in ("hochladen", "ohne"):
            raise Ablehnung("invalid", "„entscheidung“ muss hochladen, ohne oder cover sein.", "entscheidung")
        if wahl == "hochladen" and data.get("bestaetigt") is not True:  # Nutzer, 14.11.2026: Upload nur nach Bestätigung
            raise Ablehnung("confirm_required", "Der Upload bei SoundCloud muss ausdrücklich bestätigt werden.",
                            "bestaetigt", 409)
        if sicht not in ("privat", "oeffentlich") or not isinstance(promo, bool):
            raise Ablehnung("invalid", "Sichtbarkeit oder Promotion sind ungültig.", "sichtbarkeit")

        def fn(order):
            n = _im_nachlauf(order)
            s = n["soundcloud"]
            if s["stand"] != "offen" or any(n[p]["stand"] not in ERLEDIGT for p in ("mastering", "cover", "text")):
                raise Ablehnung("invalid_transition", "Über SoundCloud lässt sich gerade nicht entscheiden.",
                                "status", 409)
            if wahl == "ohne":
                s.update(stand="ausgelassen", fehler="")
                eintrag(order, NUTZER, "status", "Kein Upload bei SoundCloud.")
                return
            s.update(stand="beauftragt", sichtbarkeit=sicht, promotion=promo, fehler="")
            eintrag(order, NUTZER, "antwort", "Bei SoundCloud hochladen: "
                    + ("öffentlich" if sicht == "oeffentlich" else "privat")
                    + (", mit Promotion." if promo else "."))
        return self.store.mutate(oid, revision(data), fn)


def _fuer_claude(order, favorit):
    """Der Song, für den Claude meldet. Bei mehreren Songs muss der Favorit genannt sein."""
    alle = nachlaeufe(order) if order["status"] in ("nachlauf", "fertig") else []
    if not alle:
        raise Ablehnung("invalid_transition", "Das geht erst, wenn der Favorit fertig gemacht wird.", "status", 409)
    if favorit:
        n = next((n for n in alle if n["favorit"] == favorit), None)
        if n is None:
            raise Ablehnung("not_found", "Dieser Song wird in diesem Auftrag nicht fertig gemacht.", "favorit", 404)
        return n, len(alle) > 1
    if len(alle) > 1:
        raise Ablehnung("required", "Mehrere Songs werden fertig gemacht; bitte --favorit angeben.", "favorit")
    return alle[0], False


def phase_melden(cfg, order, name, pfad=None, text="", tags=(), link="", fehler="", favorit=None):
    """Claude meldet das Ergebnis einer Phase. `pfad` ist bereits relativ zum Musikordner."""
    n, mehrere = _fuer_claude(order, favorit)
    song = f" ({parse_pfad(n['favorit'])['titel']})" if mehrere else ""
    if name not in ("ableton", "cover", "text", "soundcloud"):
        raise Ablehnung("invalid", "„name“ muss ableton, cover, text oder soundcloud sein.", "name")
    p = n[name]
    if name in ("ableton", "soundcloud") and p["stand"] != "beauftragt":
        raise Ablehnung("invalid_transition", "Dafür liegt kein Ja des Nutzers vor.", "status", 409)
    if fehler:
        if name == "cover":
            p.update(stand="wartet", datei="", fehler=fehler)
        elif name == "text":
            p.update(stand="ausgelassen")
        elif name == "ableton":
            p.update(stand="offen", notiz=f"Nicht gelungen: {fehler}")
        else:
            p.update(stand="offen", fehler=fehler)
        eintrag(order, CLAUDE, "status", f"{name.capitalize()} ist nicht gelungen{song}: {fehler}")
        return
    if name == "cover":
        if p["stand"] != "offen":
            raise Ablehnung("invalid_transition", "Gerade ist kein Cover angefordert.", "status", 409)
        if p["versuche"] >= MAX_COVER:
            raise Ablehnung("limit", f"Mehr als {MAX_COVER} Cover je Song sind nicht vorgesehen.", "name", 409)
        p.update(stand="wartet", datei=pfad, versuche=p["versuche"] + 1, fehler="")
        eintrag(order, CLAUDE, "status", f"Das Cover liegt vor{song}.")
    elif name == "text":
        inhalt = safe_audio_path(cfg.music_root, pfad, "file", TEXT_EXT).read_text(encoding="utf-8-sig")
        p.update(stand="fertig", datei=pfad, beschreibung=inhalt.strip()[:20000],
                 tags=[t.strip() for t in tags if t.strip()][:30])
        eintrag(order, CLAUDE, "status", f"Songbeschreibung und Songtext liegen beim Song{song}.")
    elif name == "ableton":
        p.update(stand="fertig", notiz=text)
        eintrag(order, CLAUDE, "status", f"Der Song liegt in Ableton{song}." + (f" {text}" if text else ""))
    else:
        if not link.startswith("https://"):
            raise Ablehnung("invalid", "Der Link muss mit https:// beginnen.", "link")
        p.update(stand="fertig", link=link, fehler="", hochgeladen_datei=endfassung(n), audio_offen=False, text_offen=False)
        eintrag(order, CLAUDE, "status", f"Bei SoundCloud hochgeladen: {link}")
