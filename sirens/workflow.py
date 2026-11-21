"""Zustände, erlaubte Übergänge und die eine Funktion für „wer ist dran“."""
from . import ablauf
from .contracts import Ablehnung

NUTZER, CLAUDE = "nutzer", "claude"

# (von, nach) -> wer den Übergang auslösen darf
UEBERGAENGE = {
    ("entwurf", "offen"): NUTZER,
    ("offen", "in_arbeit"): CLAUDE,
    ("in_arbeit", "rueckfrage"): CLAUDE,
    ("in_arbeit", "plan_wartet"): CLAUDE,
    ("in_arbeit", "gesendet"): CLAUDE,
    ("in_arbeit", "fehler"): CLAUDE,
    ("rueckfrage", "antwort_da"): NUTZER,
    ("plan_wartet", "antwort_da"): NUTZER,
    ("antwort_da", "in_arbeit"): CLAUDE,
    ("gesendet", "fertig"): CLAUDE,
    ("gesendet", "fehler"): CLAUDE,
    ("fertig", "abgeschlossen"): NUTZER,
    ("fertig", "nachlauf"): NUTZER,
    ("abgeschlossen", "nachlauf"): NUTZER,
    ("nachlauf", "abgeschlossen"): NUTZER,
    ("nachlauf", "fertig"): NUTZER,
    ("fehler", "in_arbeit"): CLAUDE,
}
for _von in ("entwurf", "offen", "in_arbeit", "rueckfrage", "plan_wartet", "antwort_da", "fehler"):
    UEBERGAENGE[(_von, "abgebrochen")] = NUTZER

STATUS = sorted({s for pair in UEBERGAENGE for s in pair})
SCHRITTE = ("geplant", "text", "paket", "geprueft", "gesendet", "fertig", "fehler")
STATIONEN = ("Auftrag", "Klären", "Plan", "Prüfen und Senden", "Anhören", "Mastering", "Cover", "Text",
             "SoundCloud", "Abschluss")
PHASEN = ("mastering", "cover", "text", "soundcloud")
ERLEDIGT = ("fertig", "ausgelassen")

_DRAN = {"entwurf": "nutzer", "offen": "claude", "in_arbeit": "laeuft", "rueckfrage": "nutzer",
         "plan_wartet": "nutzer", "antwort_da": "claude", "gesendet": "laeuft", "fertig": "nutzer",
         "abgeschlossen": "niemand", "fehler": "claude", "abgebrochen": "niemand", "nachlauf": "nutzer"}

_SATZ = {
    "entwurf": "Entwurf fertig ausfüllen und abschicken.",
    "offen": "Claude legt los.",
    "rueckfrage": "Claude hat eine Frage. Bitte beantworten.",
    "plan_wartet": "Der Plan liegt vor. Bitte freigeben oder Änderungen schreiben.",
    "antwort_da": "Claude macht mit deiner Antwort weiter.",
    "gesendet": "Die Songs werden erzeugt. Sie erscheinen hier, sobald sie fertig sind.",
    "fertig": "Die Songs sind fertig. Bitte anhören und bewerten.",
    "abgeschlossen": "Abgeschlossen.",
    "fehler": "Es gab einen Fehler. Claude nimmt den Auftrag wieder auf.",
    "abgebrochen": "Abgebrochen.",
    "nachlauf": "Der Favorit wird fertig gemacht.",
}


def wechsel(order, nach, wer):
    """Status ändern, wenn der Übergang erlaubt ist; sonst ablehnen."""
    von = order["status"]
    erlaubt = UEBERGAENGE.get((von, nach))
    if erlaubt is None or erlaubt != wer:
        raise Ablehnung("invalid_transition", f"Vom Status „{von}“ ist „{nach}“ hier nicht möglich.", "status", 409)
    order["status"] = nach


def offene_bewertungen(order):
    return [b for b in order.get("bewertungen", []) if not b.get("uebernommen")]


def nachlaeufe(order):
    """Alle Songs, die fertig gemacht werden: der gerade gezeigte zuerst, dann die zurückgestellten."""
    return [n for n in (order.get("nachlauf"), *order.get("nachlauf_weitere", [])) if n]


def claude_phasen(n):
    """Phasen eines Songs, die gerade auf Claude warten."""
    master = n["mastering"]["stand"] in ERLEDIGT
    offen = {"ableton": n["ableton"]["stand"] == "beauftragt", "cover": master and n["cover"]["stand"] == "offen",
             "text": master and n["text"]["stand"] == "offen", "soundcloud": n["soundcloud"]["stand"] == "beauftragt"}
    return [name for name, an in offen.items() if an]


def nachlauf_lage(n):
    """Wer im Nachlauf dran ist: (dran, Station, Satz). Die erste nicht erledigte Phase entscheidet."""
    stand = {name: n[name]["stand"] for name in PHASEN}
    if stand["mastering"] not in ERLEDIGT:
        return NUTZER, 6, "Bitte den Master wählen: im Studio rendern, automatisch mastern, eigene Datei oder ohne Mastering."
    if n["ableton"]["stand"] == "beauftragt":
        return CLAUDE, 6, "Claude legt den Song in Ableton an."
    if stand["cover"] == "offen":
        return CLAUDE, 7, "Claude erstellt das Cover und die Songbeschreibung."
    if stand["cover"] == "wartet":
        return NUTZER, 7, "Das Cover liegt vor. Bitte annehmen oder ein neues anfordern."
    if stand["text"] not in ERLEDIGT:
        return CLAUDE, 8, "Claude schreibt die Songbeschreibung mit Songtext."
    if stand["soundcloud"] == "offen":
        return NUTZER, 9, "Bitte entscheiden: bei SoundCloud hochladen?"
    if stand["soundcloud"] == "beauftragt":
        return CLAUDE, 9, "Claude lädt den Song bei SoundCloud hoch."
    if stand["soundcloud"] == "fertig" and any(n["soundcloud"].get(k) for k in
                                               ("cover_offen", "text_offen", "audio_offen")):
        return NUTZER, 9, "Lokale Fassung geändert. Bitte den bestehenden SoundCloud-Track aktualisieren."
    return NUTZER, 10, "Alles erledigt. Bitte abschließen."


def ausgelassen(order):
    """Stationen 6–9, die ausgelassen wurden (bei abgeschlossenen Aufträgen auch alle nicht erledigten)."""
    n = order.get("nachlauf")
    davor = [2, 3, 4, 5] if n and (n.get("vorhanden") or n.get("nur_mastern")) else []  # vorhandener Song: nie geplant oder erzeugt
    if order["status"] != "abgeschlossen":
        return davor + [6 + i for i, name in enumerate(PHASEN) if n and n[name]["stand"] == "ausgelassen"]
    return davor + [6 + i for i, name in enumerate(PHASEN) if not n or n[name]["stand"] != "fertig"]


def _station(order):
    status = order["status"]
    fest = {"entwurf": 1, "offen": 1, "rueckfrage": 2, "plan_wartet": 3, "gesendet": 4, "fertig": 5,
            "abgeschlossen": 10}
    if status in fest:
        return fest[status]
    if status == "nachlauf":
        return nachlauf_lage(order["nachlauf"])[1]
    if status in ("in_arbeit", "antwort_da", "fehler"):
        weit = any(t.get("schritt") in ("paket", "geprueft", "gesendet", "fertig") for t in order.get("tracks_stand", []))
        return 4 if weit else 3 if order.get("plan") else 2
    return 0


# Feste Texte des Verlaufs (Anfang genügt) -> Station, an der sie entstehen
_TEXT_STATION = (
    ("Auftrag abgeschickt", 1), ("Claude hat den Auftrag übernommen", 2), ("Der Plan liegt zur Freigabe", 3),
    ("Plan freigegeben", 3), ("Die Songs sind zur Erzeugung", 4), ("Die Songs sind fertig", 5), ("Zurück zum Anhören", 5),
    ("Vorhandenen Song fertig machen", 6), ("Favorit wird fertig gemacht", 6), ("Ohne Mastering", 6), ("Master gewählt", 6),
    ("Mastering ist nicht", 6), ("Bitte nach Ableton", 6), ("Der Song liegt in Ableton", 6), ("Ableton ist nicht", 6),
    ("Ohne Cover", 7), ("Cover angenommen", 7), ("Bitte ein neues Cover", 7), ("Das Cover liegt vor", 7), ("Cover gewählt", 7), ("Cover bei SoundCloud ersetzt", 9), ("Cover ist nicht", 7),
    ("Songbeschreibung und Songtext", 8), ("Text ist nicht", 8),
    ("Kein Upload", 9), ("Bei SoundCloud", 9), ("Soundcloud ist nicht", 9), ("Auftrag abgeschlossen", 10),
)
_ART_STATION = {"rueckfrage": 2, "plan_aenderung": 3}


def station_jetzt(order):
    """Station, an der gerade gearbeitet wird (für freie Einträge wie Notizen und Antworten)."""
    if order["status"] == "in_arbeit" and order.get("detail_schritt") in ablauf.NAMEN:
        return ablauf.STATION.get(order["detail_schritt"], 4)
    return _station(order)


def verlauf_stationen(order):
    """Je Verlaufseintrag die Station: fester Text, sonst der beim Schreiben gemerkte Stand, sonst wie der Eintrag davor."""
    station, liste = 1, []
    for e in order.get("verlauf", []):
        fest = next((nr for anfang, nr in _TEXT_STATION if e["text"].startswith(anfang)), None)
        station = fest or _ART_STATION.get(e["art"]) or e.get("station") or station
        liste.append(station)
    return liste


def lage(order):
    """Wer ist dran, welche Station, nächster Schritt als Satz. Seite und CLI nutzen genau diese Funktion."""
    status = order["status"]
    dran, satz = _DRAN[status], _SATZ.get(status)
    if status == "in_arbeit":
        satz = "Claude arbeitet gerade daran."
    auch = False
    if status == "nachlauf":
        n = order["nachlauf"]
        dran, _, satz = nachlauf_lage(n)
    if status in ("nachlauf", "fertig"):  # auch zurückgestellte Songs können auf Claude warten
        auch = any(claude_phasen(n) for n in nachlaeufe(order))
    offen = len(offene_bewertungen(order))
    if offen and dran in ("niemand", "nutzer") and status in ("fertig", "abgeschlossen"):
        if status == "abgeschlossen":
            dran = "claude"
            satz = "Claude übernimmt noch deine Bewertungen."
    return {"dran": dran, "claude_auch_dran": bool(offen) or auch or dran == "claude",
            "station": _station(order), "stationen": list(STATIONEN), "ausgelassen": ausgelassen(order),
            "detail": ablauf.detail(order), "verlauf_station": verlauf_stationen(order),
            "naechster_schritt": satz, "offene_bewertungen": offen}
