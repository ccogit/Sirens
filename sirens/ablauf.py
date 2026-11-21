"""Die einzelnen Arbeitsschritte bis zum Versand – und welche davon ein Auftrag verkürzt oder auslässt.

Eine Quelle für Formular (Vorschau), Auftragsansicht (Fortschritt) und CLI (`detail`).
"""
# Name, Titel, wer
SCHRITTE = (
    ("lesen", "Auftrag lesen und Vorbilder in der Datenbank nachschlagen", "Claude"),
    ("rueckfrage", "Rückfrage, falls etwas Entscheidendes fehlt", "Claude, du"),
    ("konzept", "Konzept, Titel und Klangbeschreibung festlegen", "Claude"),
    ("planfreigabe", "Plan freigeben", "du"),
    ("text", "Songtext schreiben", "Claude"),
    ("paket", "Paket für den Anbieter bauen und formal prüfen", "automatisch"),
    ("abgleich", "Texte des Albums untereinander abgleichen", "Claude"),
    ("zweitgutachten", "Zusatzprüfung durch ein zweites, unabhängiges Gutachten", "Claude"),
    ("korrektur", "Verbesserungen aus der Zusatzprüfung einarbeiten", "Claude"),
    ("klang", "Klangprüfung der Beschreibung (Signature-HQ)", "Claude"),
    ("freigabe", "Freigabeprüfung mit Web-Stichprobe auf ähnliche Songs", "Claude"),
    ("senden", "An den Anbieter senden", "automatisch"),
    ("download", "Takes herunterladen", "automatisch"),
)
NAMEN = tuple(name for name, _, _ in SCHRITTE)
# Station (siehe workflow.STATIONEN), zu der ein Arbeitsschritt gehört: Klären, Plan, sonst Prüfen und Senden
STATION = {"lesen": 2, "rueckfrage": 2, "konzept": 3, "planfreigabe": 3}


def plan(wunsch):
    """Je Schritt: `voll`, `kurz` (verkürzt) oder `entfaellt`, mit Begründung."""
    optionen = (wunsch or {}).get("optionen") or {}
    schnell = optionen.get("tempo") == "schnell"
    album = (wunsch or {}).get("umfang") == "album"
    ohne_gutachten = optionen.get("zweitgutachten") == "aus"
    regeln = {
        "rueckfrage": ("entfaellt", "Fast Mode: Claude entscheidet selbst") if schnell else None,
        "konzept": ("kurz", "Fast Mode: ohne Web-Recherche") if schnell else None,
        "planfreigabe": None if optionen.get("planfreigabe") == "an" and not schnell
        else ("entfaellt", "Fast Mode" if schnell else "nicht gewünscht"),
        "text": ("kurz", "Fast Mode: ein Durchlauf, keine Verbesserungsrunde") if schnell else None,
        "abgleich": ("entfaellt", "Fast Mode") if schnell and album else None if album else ("entfaellt", "nur bei Alben"),
        "zweitgutachten": ("entfaellt", "Fast Mode" if schnell else "von dir ausgeschaltet") if ohne_gutachten or schnell else None,
        "korrektur": ("entfaellt", "ohne Zusatzprüfung gibt es keine") if ohne_gutachten or schnell else None,
        "freigabe": ("kurz", "Fast Mode: ohne Web-Stichprobe") if schnell else None,
    }
    return [{"name": name, "titel": titel, "wer": wer, "station": STATION.get(name, 4), "art": (regeln.get(name) or ("voll", ""))[0],
             "hinweis": (regeln.get(name) or ("voll", ""))[1]} for name, titel, wer in SCHRITTE]


def detail(order):
    """Plan mit Stand: erledigt, aktiv, offen oder entfaellt. Vorhandene Songs haben keinen solchen Ablauf."""
    if (order.get("nachlauf") or {}).get("vorhanden") or (order.get("nachlauf") or {}).get("nur_mastern"):
        return []
    status = order["status"]
    aktuell = order.get("detail_schritt")
    if status in ("fertig", "nachlauf", "abgeschlossen"):
        bis, aktiv = len(NAMEN), None
    elif status == "gesendet":
        bis, aktiv = NAMEN.index("download"), "download"
    elif status in ("entwurf", "offen", "abgebrochen") or aktuell not in NAMEN:
        bis, aktiv = 0, None
    else:
        bis, aktiv = NAMEN.index(aktuell), aktuell if status in ("in_arbeit", "rueckfrage", "plan_wartet") else None
    schritte = plan(order.get("wunsch"))
    for i, schritt in enumerate(schritte):
        schritt["zustand"] = ("entfaellt" if schritt["art"] == "entfaellt" else "erledigt" if i < bis
                              else "aktiv" if schritt["name"] == aktiv else "offen")
    return schritte
