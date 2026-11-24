"""Führt die bisherige Stil-Ordnerstruktur in Alben/ und Singles/ zusammen."""
import argparse
import json
import re
import tempfile
from pathlib import Path

from .musikablage import METADATEN
from .migrate_music_db import MusicmakerPfade


def lese_json(datei):
    return json.loads(datei.read_text(encoding="utf-8-sig"))


def schreibe_json(datei, daten):
    with tempfile.NamedTemporaryFile(dir=datei.parent, delete=False, mode="w", encoding="utf-8") as stream:
        temp = Path(stream.name)
        try:
            stream.write(json.dumps(daten, ensure_ascii=False, indent=2) + "\n")
            stream.close()
            temp.replace(datei)
        finally:
            temp.unlink(missing_ok=True)


def migrationsplan(root, stile):
    belegt = {}
    for gruppe in ("Alben", "Singles"):
        ordner = root / gruppe
        belegt[gruppe] = {p.name.casefold() for p in ordner.iterdir()} if ordner.is_dir() else set()
    plan = {}
    for stil in sorted(stile):
        basis = root / stil
        for release in sorted(basis.iterdir()):
            if not release.is_dir() or release.is_symlink():
                raise ValueError(f"Unerwarteter Eintrag in der Stil-Ablage: {release}")
            if release.name.casefold() == "singles":
                for single in sorted(release.iterdir()):
                    if not single.is_dir() or single.is_symlink():
                        raise ValueError(f"Single ohne eigenen Songordner: {single}")
                    ziel_festlegen(root, single, stil, "Singles", belegt, plan)
            else:
                ziel_festlegen(root, release, stil, "Alben", belegt, plan)
    return plan


def ziel_festlegen(root, quelle, stil, gruppe, belegt, plan):
    name = quelle.name
    if name.casefold() in belegt[gruppe]:
        name = f"{name}--{stil}"
        nummer = 2
        while name.casefold() in belegt[gruppe]:
            name = f"{quelle.name}--{stil}-{nummer}"
            nummer += 1
    belegt[gruppe].add(name.casefold())
    plan[quelle.relative_to(root).as_posix()] = f"{gruppe}/{name}"


def pfad_ersetzen(wert, plan):
    """Relative und absolute Musikpfade erhalten ihre bisherige Schreibweise."""
    normal = wert.replace("\\", "/")
    treffer = re.search(r"(?:^|/)generated-music/", normal, re.IGNORECASE)
    start = treffer.end() if treffer else 0
    teil = normal[start:]
    for alt, neu in plan.items():
        if teil.casefold() == alt.casefold() or teil.casefold().startswith(alt.casefold() + "/"):
            if "\\" in wert and "/" not in wert:
                neu = neu.replace("/", "\\")
            return wert[:start] + neu + wert[start + len(alt):]
    return wert


def daten_umschreiben(wert, plan):
    if isinstance(wert, str):
        return pfad_ersetzen(wert, plan)
    if isinstance(wert, list):
        return [daten_umschreiben(k, plan) for k in wert]
    if isinstance(wert, dict):
        neu = {pfad_ersetzen(k, plan): daten_umschreiben(v, plan) for k, v in wert.items()}
        if len(neu) != len(wert):
            raise ValueError("Die Migration würde zwei JSON-Schlüssel zusammenführen.")
        return neu
    return wert


def release_titel(ordner):
    info = ordner / "Album-info.txt"
    if not info.is_file():
        return ordner.name.replace("-", " ")
    with info.open(encoding="utf-8-sig") as stream:
        return next((zeile.strip() for zeile in stream if zeile.strip()), ordner.name)


def vorbereiten(root, data_dir, plan):
    dateien = [data_dir / "katalog-bewertungen.json", root / "_soundcloud" / "cco_music.json"]
    for gruppe in ("auftraege", "spielzeug", "stems"):
        dateien.extend(sorted((data_dir / gruppe).rglob("*.json")))
    aenderungen = {}
    for datei in dateien:
        if not datei.is_file():
            continue
        daten = lese_json(datei)
        neu = daten_umschreiben(daten, plan)
        if neu != daten:
            aenderungen[datei] = neu
    return aenderungen


def migrieren(root, data_dir, stile, anwenden=False, musicmaker=None):
    root = root.resolve(strict=True)
    data_dir = data_dir.resolve(strict=True)
    for stil in stile:
        if Path(stil).name != stil or stil.startswith((".", "_")) or stil.casefold() in {"alben", "singles"}:
            raise ValueError(f"Ungültiger Stilordner: {stil}")
        ordner = root / stil
        if not ordner.is_dir() or ordner.resolve().parent != root:
            raise ValueError(f"Stilordner fehlt oder liegt außerhalb der Musikablage: {stil}")
    plan = migrationsplan(root, set(stile))
    aenderungen = vorbereiten(root, data_dir, plan)
    db_plan = musicmaker.planen(lambda pfad: pfad_ersetzen(pfad, plan)) if musicmaker and plan else {}
    print(json.dumps({"ordner": plan, "json_dateien": [str(p) for p in aenderungen],
                      "datenbankfelder": {f"{t}.{s}": len(daten) for (t, s), daten in db_plan.items()}},
                     ensure_ascii=False, indent=2))
    if not anwenden or not plan:
        return
    katalog = root / "_sirens"
    katalog.mkdir(exist_ok=True)
    belege = Path(tempfile.mkdtemp(prefix="strukturmigration-", dir=katalog))
    print(f"Pfadprotokoll und Sicherungen: {belege}")
    rueckweg = []
    geaendert = {}
    neu_metadaten = []
    gruppen = [root / "Alben", root / "Singles"]
    try:
        for nr, datei in enumerate(aenderungen):
            sicherung = belege / f"{nr:03}.json"
            sicherung.write_bytes(datei.read_bytes())
            geaendert[datei] = sicherung
        schreibe_json(belege / "pfadzuordnung.json", {"ordner": plan, "sicherungen": {
            str(k): v.name for k, v in geaendert.items()}})
        if db_plan:
            schreibe_json(belege / "musicmaker-pfade.json", {f"{t}.{s}": daten for (t, s), daten in db_plan.items()})
        for gruppe in gruppen:
            gruppe.mkdir(exist_ok=True)
        for alt, neu in plan.items():
            quelle, ziel = root / alt, root / neu
            if ziel.exists():
                raise FileExistsError(ziel)
            if quelle.resolve().parent not in {root / alt.split("/")[0], root / alt.rsplit("/", 1)[0]}:
                raise ValueError(f"Release liegt außerhalb der vorgesehenen Ablage: {quelle}")
            meta = quelle / METADATEN
            if not meta.exists():
                schreibe_json(meta, {"stilreferenz": alt.split("/")[0], "slug": quelle.name, "titel": release_titel(quelle)})
                neu_metadaten.append((quelle, ziel))
            quelle.rename(ziel)
            rueckweg.append((quelle, ziel))
        for datei, daten in aenderungen.items():
            if datei.read_bytes() != geaendert[datei].read_bytes():
                raise RuntimeError(f"Die Datei wurde während der Migration geändert: {datei}")
            schreibe_json(datei, daten)
            geaendert[datei] = (geaendert[datei], datei.read_bytes())
        if db_plan:
            musicmaker.anwenden(db_plan)
    except BaseException:
        for datei, beleg in geaendert.items():
            if isinstance(beleg, tuple) and datei.read_bytes() == beleg[1]:
                datei.write_bytes(beleg[0].read_bytes())
        for quelle, ziel in reversed(rueckweg):
            ziel.rename(quelle)
        for quelle, _ in neu_metadaten:
            (quelle / METADATEN).unlink()
        raise
    for stil in set(stile):
        basis = root / stil
        for ordner in basis.iterdir():
            if not any(ordner.iterdir()):
                ordner.rmdir()
        if not any(basis.iterdir()):
            basis.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("stile", nargs="+")
    parser.add_argument("--anwenden", action="store_true")
    parser.add_argument("--musicmaker-container", help="Musicmaker-PostgreSQL-Container in Podman")
    args = parser.parse_args()
    musicmaker = MusicmakerPfade(args.musicmaker_container) if args.musicmaker_container else None
    migrieren(args.root, args.data_dir, args.stile, args.anwenden, musicmaker)


if __name__ == "__main__":
    main()
