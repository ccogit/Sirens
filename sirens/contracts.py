"""Auftragsmodell: Prüfung des Wunsch-Teils und sichere Pfade im Musikordner."""
import re
from pathlib import Path, PurePosixPath

from .musikablage import ablage, release_metadaten

SCHEMA_VERSION = 1
AUDIO_EXT = (".mp3", ".wav", ".flac")
BILD_EXT = (".png", ".jpg", ".jpeg", ".webp")
TEXT_EXT = (".txt", ".md")
ID_RE = re.compile(r"^SA-\d{8}-\d{3}$")
NAME_RE = re.compile(r"^(?P<titel>.+?) - Version (?P<version>\d+)(?P<fassung>.*)$")

WEGE = ("referenz", "beschreibung")
UMFANG = ("song", "album")
BEZUG = ("im_stil", "fortsetzung", "neufassung")
GEWICHT = ("normal", "stark")
OPTIONEN = {
    "titelwunsch": None, "sprache": None, "no_gos": None,
    "gesang": ("mit", "instrumental", "egal"),
    "provider": ("suno", "minimax"),
    "planfreigabe": ("aus", "an"),
    "zweitgutachten": ("an", "aus"),
    "tempo": ("normal", "schnell"),
}
WUNSCH_FELDER = ("weg", "umfang", "track_count", "artist_slug", "ziel_release_slug", "bezug",
                 "referenzen", "wunsch", "track_wuensche", "optionen")
MAX_REFERENZEN = 12
MAX_TEXT = 8000


class Ablehnung(Exception):
    """Fachliche Ablehnung mit Code, betroffenem Feld und deutscher Meldung."""

    def __init__(self, code, meldung, feld=None, status=400):
        super().__init__(meldung)
        self.code, self.meldung, self.feld, self.status = code, meldung, feld, status

    def as_dict(self):
        return {"error": self.code, "meldung": self.meldung, "feld": self.feld}


def _text(value, feld, pflicht=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise Ablehnung("invalid", f"„{feld}“ muss Text sein.", feld)
    value = value.strip()
    if len(value) > MAX_TEXT:
        raise Ablehnung("invalid", f"„{feld}“ ist zu lang (höchstens {MAX_TEXT} Zeichen).", feld)
    if pflicht and not value:
        raise Ablehnung("required", f"„{feld}“ fehlt.", feld)
    return value


def _wahl(value, erlaubt, feld, standard):
    if value in (None, ""):
        return standard
    if value not in erlaubt:
        raise Ablehnung("invalid", f"„{feld}“ muss einer dieser Werte sein: {', '.join(erlaubt)}.", feld)
    return value


def safe_audio_path(music_root, pfad, feld="pfad", endungen=AUDIO_EXT):
    """Relativen Pfad prüfen und als absolute Datei im Musikordner zurückgeben."""
    if not isinstance(pfad, str) or not pfad.strip():
        raise Ablehnung("invalid_path", "Der Pfad fehlt.", feld)
    raw = pfad.strip()
    if "\\" in raw or raw.startswith("/") or ":" in raw or "\x00" in raw:
        raise Ablehnung("invalid_path", "Der Pfad muss relativ zum Musikordner sein und „/“ verwenden.", feld)
    parts = PurePosixPath(raw).parts
    if not parts or any(p in ("..", ".") for p in parts):
        raise Ablehnung("invalid_path", "Der Pfad darf den Musikordner nicht verlassen.", feld)
    if PurePosixPath(raw).suffix.lower() not in endungen:
        raise Ablehnung("invalid_path", f"Nur {' und '.join(endungen)} sind erlaubt.", feld)
    root = Path(music_root).resolve()
    target = root.joinpath(*parts).resolve()
    if root != target and root not in target.parents:
        raise Ablehnung("invalid_path", "Der Pfad darf den Musikordner nicht verlassen.", feld)
    return target


def parse_pfad(pfad, music_root=None):
    """Stilreferenz, Release, Titel, Version und Fassung aus Pfad und Release-Metadaten."""
    stil, release, _ = ablage(pfad)
    if music_root is not None:
        metadaten = release_metadaten(Path(music_root), pfad)
        stil = metadaten.get("stilreferenz") or stil
        release = metadaten.get("slug") or release
    stem = PurePosixPath(pfad).stem
    match = NAME_RE.match(stem)
    return {
        "artist_slug": stil,
        "release_slug": release,
        "titel": match.group("titel").strip() if match else stem,
        "version": int(match.group("version")) if match else None,
        "fassung": match.group("fassung").strip() if match else "",
    }


def _referenzen(value, music_root):
    if value is None:
        return []
    if not isinstance(value, list):
        raise Ablehnung("invalid", "„referenzen“ muss eine Liste sein.", "referenzen")
    if len(value) > MAX_REFERENZEN:
        raise Ablehnung("invalid", f"Höchstens {MAX_REFERENZEN} Referenzen.", "referenzen")
    result, seen = [], set()
    for i, ref in enumerate(value):
        feld = f"referenzen[{i}]"
        if not isinstance(ref, dict):
            raise Ablehnung("invalid", "Eine Referenz muss ein Objekt sein.", feld)
        erlaubt = {"pfad", "gewicht", "uebernehmen", "artist_slug", "release_slug", "titel", "version", "fassung"}
        unbekannt = set(ref) - erlaubt
        if unbekannt:
            raise Ablehnung("unknown_field", f"Unbekanntes Feld: {sorted(unbekannt)[0]}.", feld)
        target = safe_audio_path(music_root, ref.get("pfad"), feld)
        if not target.is_file():
            raise Ablehnung("missing_file", f"Die Datei gibt es nicht: {ref.get('pfad')}", feld)
        pfad = ref["pfad"].strip()
        if pfad in seen:
            continue
        seen.add(pfad)
        result.append({"pfad": pfad, **parse_pfad(pfad, music_root),
                       "gewicht": _wahl(ref.get("gewicht"), GEWICHT, feld + ".gewicht", "normal"),
                       "uebernehmen": _text(ref.get("uebernehmen"), feld + ".uebernehmen")})
    return result


def _track_wuensche(value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise Ablehnung("invalid", "„track_wuensche“ muss eine Liste sein.", "track_wuensche")
    result = []
    for i, item in enumerate(value):
        feld = f"track_wuensche[{i}]"
        if not isinstance(item, dict) or set(item) - {"nr", "text"}:
            raise Ablehnung("invalid", "Ein Songwunsch braucht nur „nr“ und „text“.", feld)
        nr = item.get("nr")
        if isinstance(nr, bool) or not isinstance(nr, int) or not 1 <= nr <= 20:
            raise Ablehnung("invalid", "„nr“ muss eine Zahl von 1 bis 20 sein.", feld)
        text = _text(item.get("text"), feld + ".text")
        if text:
            result.append({"nr": nr, "text": text})
    return result


def _optionen(value):
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise Ablehnung("invalid", "„optionen“ muss ein Objekt sein.", "optionen")
    unbekannt = set(value) - set(OPTIONEN)
    if unbekannt:
        raise Ablehnung("unknown_field", f"Unbekannte Option: {sorted(unbekannt)[0]}.", "optionen")
    result = {}
    for name, erlaubt in OPTIONEN.items():
        feld = f"optionen.{name}"
        result[name] = _text(value.get(name), feld) if erlaubt is None else _wahl(value.get(name), erlaubt, feld, erlaubt[0])
    if result["tempo"] == "schnell":  # Fast Mode: ohne Halt und ohne Zusatzprüfung
        result.update(planfreigabe="aus", zweitgutachten="aus")
    return result


def validate_wunsch(data, music_root, vollstaendig):
    """Wunsch-Teil prüfen und normalisieren. Entwürfe dürfen unvollständig sein, abgeschickte Aufträge nicht."""
    if not isinstance(data, dict):
        raise Ablehnung("invalid", "Der Auftrag muss ein Objekt sein.")
    unbekannt = set(data) - set(WUNSCH_FELDER)
    if unbekannt:
        raise Ablehnung("unknown_field", f"Unbekanntes Feld: {sorted(unbekannt)[0]}.", sorted(unbekannt)[0])
    wunsch = {
        "weg": _wahl(data.get("weg"), WEGE, "weg", "referenz"),
        "umfang": _wahl(data.get("umfang"), UMFANG, "umfang", "song"),
        "artist_slug": _text(data.get("artist_slug"), "artist_slug"),
        "ziel_release_slug": _text(data.get("ziel_release_slug"), "ziel_release_slug"),
        "bezug": _wahl(data.get("bezug"), BEZUG, "bezug", "im_stil"),
        "referenzen": _referenzen(data.get("referenzen"), music_root),
        "wunsch": _text(data.get("wunsch"), "wunsch"),
        "track_wuensche": _track_wuensche(data.get("track_wuensche")),
        "optionen": _optionen(data.get("optionen")),
    }
    count = data.get("track_count")
    if count in (None, ""):
        count = None
    elif isinstance(count, bool) or not isinstance(count, int) or not 2 <= count <= 20:
        raise Ablehnung("invalid", "Die Anzahl der Songs muss zwischen 2 und 20 liegen.", "track_count")
    wunsch["track_count"] = count if wunsch["umfang"] == "album" else None
    if wunsch["umfang"] == "song":
        wunsch["track_wuensche"] = []
    if vollstaendig:
        if wunsch["weg"] == "referenz" and not wunsch["referenzen"]:
            raise Ablehnung("required", "Bitte mindestens einen Referenzsong wählen.", "referenzen")
        if wunsch["weg"] == "beschreibung" and not wunsch["wunsch"]:
            raise Ablehnung("required", "Bitte beschreiben, was entstehen soll.", "wunsch")
        if not wunsch["artist_slug"]:
            raise Ablehnung("required", "Bitte einen Künstler angeben.", "artist_slug")
    return wunsch
