"""Einheitliche Kurzprofile für alle lokal spielbaren Songs."""
import argparse
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

DATEINAME = ".sirens-songprofile.json"


def kurzprofil(release, song):
    dateien = song["dateien"]
    formate = sorted({Path(d["pfad"]).suffix[1:].upper() for d in dateien})
    soundcloud = song.get("soundcloud", [])
    genres = sorted({i["genre"] for i in soundcloud if i.get("genre")}, key=str.casefold)
    tags = sorted({t for i in soundcloud for t in i.get("tags", [])}, key=str.casefold)
    bewertungen = [d["bewertung"]["score"] for d in dateien if d.get("bewertung")]
    beschreibung = " ".join((song.get("beschreibung") or "").split())
    ausdruecklich = [beschreibung, *(i.get("beschreibung", "") for i in soundcloud)]
    tempos = {int(bpm) for text in ausdruecklich for bpm in
              re.findall(r"\b(\d{2,3})\s*BPM\b", text, re.I) if 40 <= int(bpm) <= 240}
    if beschreibung:
        zweiter_satz = re.match(r".{35,}?[.!?](?=\s|$)", beschreibung)
        if zweiter_satz:
            beschreibung = zweiter_satz.group()
        if len(beschreibung) > 230:
            beschreibung = beschreibung[:229].rsplit(" ", 1)[0] + "…"
        quelle = "Vorhandene Songbeschreibung"
    else:
        bezug = "Single" if release["single"] else f'Albumtitel aus „{release["titel"]}“'
        stil = f' mit Stilreferenz {release["stilreferenz"]}' if release.get("stilreferenz") else ""
        fassungen = "eine lokale Fassung" if len(dateien) == 1 else f"{len(dateien)} lokale Fassungen"
        beschreibung = f'{bezug}{stil}. Verfügbar in {fassungen} ({", ".join(formate)}).'
        quelle = "Katalogdaten"
    return {
        "beschreibung": beschreibung,
        "quelle": quelle,
        "typ": "Single" if release["single"] else "Albumtitel",
        "stilreferenz": release.get("stilreferenz") or None,
        "tempo_bpm": next(iter(tempos)) if len(tempos) == 1 else None,
        "soundcloud_genres": genres,
        "soundcloud_tags": tags,
        "soundcloud_zugeordnet": bool(soundcloud),
        "fassungen": len(dateien),
        "formate": formate,
        "lyrics_lokal": bool(song.get("lyrics_vorhanden")),
        "songcover_lokal": bool(song.get("cover")),
        "beste_bewertung": max(bewertungen, default=None),
    }


def speichern(cfg):
    from .catalog import Katalog, bekannte_bewertungen
    from .store import Store

    katalog = Katalog(cfg)
    katalog.scan()
    daten = katalog.baum(bekannte_bewertungen(cfg, Store(cfg)))
    anzahl = 0
    for release in daten["releases"]:
        songs = {song["titel"]: song["kurzprofil"] for song in release["songs"]}
        if not songs:
            continue
        ordner = cfg.music_root / release["pfad"]
        with NamedTemporaryFile(dir=ordner, delete=False, mode="w", encoding="utf-8") as temp:
            pfad = Path(temp.name)
            try:
                json.dump({"schema_version": 1, "songs": songs}, temp, ensure_ascii=False, indent=2)
                temp.write("\n")
                temp.close()
                pfad.replace(ordner / DATEINAME)
            finally:
                pfad.unlink(missing_ok=True)
        anzahl += len(songs)
    return anzahl


def main():
    from .config import load

    argparse.ArgumentParser(description=__doc__).parse_args()
    print(f"Kurzprofile gespeichert: {speichern(load())}")


if __name__ == "__main__":
    main()
