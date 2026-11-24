"""Metadaten für die gemeinsame Album- und Single-Ablage."""
import json
from functools import lru_cache
from pathlib import PurePosixPath

METADATEN = ".sirens-release.json"


def ablage(pfad):
    """Liefert Stilreferenz aus Altstruktur, Release und Zahl der Ordner bis zum Release."""
    teile = PurePosixPath(pfad).parts
    if len(teile) >= 3 and teile[0].casefold() in {"alben", "singles"}:
        return "", teile[1], 2
    if len(teile) >= 4 and teile[1].casefold() == "singles":
        return teile[0], teile[2], 3
    if len(teile) >= 3:
        return teile[0], teile[1], 2
    return "", "", 0


def ist_single(pfad):
    teile = PurePosixPath(pfad).parts
    return any(teil.casefold() == "singles" for teil in teile[:2])


@lru_cache(maxsize=512)
def _lesen(datei, stand):
    try:
        daten = json.loads(datei.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(daten, dict):
        return {}
    return {key: wert for key, wert in daten.items() if isinstance(wert, str)}


def release_metadaten(root, pfad):
    """Der Release-Ordner trägt Stilreferenz und Anzeigenamen für alle seine Dateien."""
    _, _, tiefe = ablage(pfad)
    if not tiefe:
        return {}
    datei = root.joinpath(*PurePosixPath(pfad).parts[:tiefe], METADATEN)
    try:
        return _lesen(datei, datei.stat().st_mtime_ns)
    except OSError:
        return {}
