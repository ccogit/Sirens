"""Lokale Track-Manifeste prüfen oder SHA-256-Werte eintragen."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

GENRES = ("Techno", "House", "Psytrance", "Industrial", "Ambient")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate(path: Path, fill_hashes: bool = False) -> dict:
    """Relative Track-Pfade beziehen sich auf den Manifestordner; nie Audio schreiben."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("tracks"), list):
        raise ValueError("Manifest benötigt eine Liste 'tracks'")
    errors = []
    for i, track in enumerate(data["tracks"], 1):
        prefix = f"Track {i}: "
        if not isinstance(track, dict):
            errors.append(prefix + "Objekt erwartet")
            continue
        if track.get("genre") not in GENRES:
            errors.append(prefix + "unbekanntes Genre")
        if not isinstance(track.get("lizenz"), str) or not track["lizenz"].strip():
            errors.append(prefix + "Lizenzhinweis fehlt")
        bpm = track.get("bpm")
        if bpm is not None and (type(bpm) not in (int, float) or not math.isfinite(bpm) or bpm <= 0):
            errors.append(prefix + "BPM muss positiv und endlich sein")
        name = track.get("pfad")
        if not isinstance(name, str) or not name.strip():
            errors.append(prefix + "Pfad fehlt")
            continue
        try:
            file = path.parent / name
            if not file.is_file():
                errors.append(prefix + "Datei fehlt")
                continue
            digest = sha256(file)
        except (OSError, ValueError):
            errors.append(prefix + "Datei nicht lesbar")
            continue
        expected = track.get("sha256")
        if fill_hashes and expected in (None, ""):
            track["sha256"] = digest
        elif not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
            errors.append(prefix + "SHA-256 fehlt oder ist ungültig")
        elif expected.lower() != digest:
            errors.append(prefix + "SHA-256 stimmt nicht")
    if errors:
        raise ValueError("\n".join(errors))
    if fill_hashes:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--fill-hashes", action="store_true", help="Nur fehlende Hashes eintragen")
    args = parser.parse_args()
    try:
        validate(args.manifest, args.fill_hashes)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Manifest ungültig: {error}\n")
    print("Manifest gültig")


if __name__ == "__main__":
    main()
