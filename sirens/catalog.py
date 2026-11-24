"""Referenzkatalog: liest den Musikordner (nur lesend) und zeigt die beste bekannte Bewertung je Datei."""
import json
import os
import re
import shlex
import threading
from pathlib import Path

from .contracts import AUDIO_EXT, BILD_EXT, parse_pfad
from .musikablage import ablage, ist_single, release_metadaten
from .songprofile import kurzprofil
from .store import jetzt

EMASTERED = re.compile(r"^eMastered_(.+?)\s+Version\s+(\d+)(.*)$", re.IGNORECASE)
INTERNE_ORDNER = {"cover-entwürfe", "lyrics-fassungen"}

RICHTUNGSWOERTER = ["treibender", "dreckiger", "mehr Funk", "lustiger", "dunkler", "wärmer", "minimaler",
                    "mehr Bass-Druck", "verspielter", "langsamer", "schneller", "mehr Überraschungen",
                    "weniger Gesang", "hypnotischer"]


def richtungswoerter(cfg):
    """Liste aus <DATA_DIR>/richtungswoerter.json, sonst die mitgelieferte Standardliste."""
    try:
        data = json.loads(cfg.direction_words_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return list(RICHTUNGSWOERTER)
    worte = [w.strip() for w in data if isinstance(w, str) and w.strip()] if isinstance(data, list) else []
    return worte or list(RICHTUNGSWOERTER)


# Die zwölf Ästhetik-Achsen eines Songs (je 0–10); sie bestimmen Form und Farbe des Emblems in der Spielwiese.
ACHSEN = ("energy", "danceability", "experimentalism", "warmth", "darkness", "psychedelia", "organicness",
          "electronicness", "melodicity", "groove", "vocal_presence", "sampling_intensity")


def bekannte_bewertungen(cfg, store):
    """{pfad: {score, label, quelle, achsen?}} aus katalog-bewertungen.json und allen Aufträgen; der höhere Wert gilt."""
    result = {}
    try:
        data = json.loads(cfg.catalog_ratings_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if isinstance(data, dict):
        for pfad, wert in data.items():
            if isinstance(wert, dict) and isinstance(wert.get("score"), int):
                result[pfad] = {"score": wert["score"], "label": str(wert.get("label") or ""), "quelle": "katalog"}
                if isinstance(wert.get("achsen"), dict):
                    result[pfad]["achsen"] = wert["achsen"]
    for order in store.list():
        for b in order.get("bewertungen", []):
            if b["pfad"] not in result or b["score"] > result[b["pfad"]]["score"]:
                achsen = result.get(b["pfad"], {}).get("achsen")  # die Achsen des Songs bleiben, auch wenn die Bewertung wechselt
                result[b["pfad"]] = {"score": b["score"], "label": f"Bewertung aus {order['id']}", "quelle": "auftrag"}
                if achsen:
                    result[b["pfad"]]["achsen"] = achsen
    return result


def _titel_schluessel(titel):
    return "".join(c for c in titel.casefold() if c.isalnum())


def _e_mastered_zuordnen(dateien):
    """Nur bei eindeutigem Ursprung normalisiert ein eMastered-Export den Songtitel."""
    bekannte_titel = {}
    for datei in dateien:
        if datei["version"] is not None:
            schluessel = datei["release_pfad"], _titel_schluessel(datei["titel"]), datei["version"]
            bekannte_titel.setdefault(schluessel, {})[datei["titel"]] = datei
    for datei in dateien:
        treffer = EMASTERED.match(datei["titel"])
        if not treffer:
            continue
        version = int(treffer[2])
        kandidaten = bekannte_titel.get((datei["release_pfad"], _titel_schluessel(treffer[1]), version), {})
        if len(kandidaten) == 1:
            original = next(iter(kandidaten.values()))
            datei.update(titel=original["titel"], version=version, fassung="eMastered" + treffer[3].replace("_", " "),
                         song_cover=original["song_cover"], track_nummer=original["track_nummer"])


def _beschreibung(text):
    return re.split(r"^\s*lyrics\s*[:\-]?\s*$", text or "", maxsplit=1, flags=re.I | re.M)[0].strip()


def _text(datei):
    try:
        return datei.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return ""


def _release_texte(ordner):
    album = []
    songs = {}
    for datei in sorted(ordner.glob("*.txt")):
        match = re.fullmatch(r"(.+) - beschreibung", datei.stem, re.I)
        if match:
            beschreibung = _beschreibung(_text(datei))
            if beschreibung:
                songs[_titel_schluessel(match[1])] = beschreibung
    for nr, zeile in enumerate(_text(ordner / "Album-info.txt").splitlines()):
        zeile = zeile.strip()
        if nr == 0 or zeile.startswith(("https://", "http://")):
            continue
        if zeile.startswith(("Titelliste", "Musicmaker-Ergänzungen", "Weitere Titel", "Albumkonzept")):
            continue
        match = re.match(r"^\d+[.)]\s+(.+?)\s+[—–-]\s+(.+)$", zeile)
        if match:
            songs.setdefault(_titel_schluessel(match[1]), match[2])
        elif len(zeile) > 60 and not re.match(r"^(?:\d+[.)]|- )\s", zeile):
            album.append(zeile)
    lyrics = {
        _titel_schluessel(match[1])
        for datei in [*ordner.glob("*.txt"), *(ordner / "Lyrics-Fassungen").glob("*.txt")]
        if (match := re.fullmatch(r"(.+) - lyrics(?: \[song \d+\])?", datei.stem, re.I))
    }
    return "\n\n".join(album), songs, lyrics


def _soundcloud_infos(root):
    """Nur belegte Pfade oder exakte Titel im zugeordneten Ordner erhalten Metadaten."""
    try:
        daten = json.loads((root / "_soundcloud" / "cco_music.json").read_text(encoding="utf-8-sig"))
        lokal = daten["local"]["tracks"]
    except (OSError, ValueError, KeyError, TypeError):
        return {}, {}, {}
    try:
        updates = json.loads((root / "_soundcloud" / "metadata-sync.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        updates = {}
    pfade, titel = {}, {}
    for track in daten.get("tracks", []):
        aktualisiert = updates.get(f"track:{track['id']}", {})
        for feld in ("description", "tag_list"):
            if isinstance(aktualisiert.get(feld), str):
                track[feld] = aktualisiert[feld]
        eintrag = lokal.get(str(track["id"]), {})
        try:
            tags = shlex.split(track.get("tag_list") or "")
        except ValueError:
            tags = []
        cover = next((ort.get("cover") for ort in eintrag.get("placements", [])
                      if ort.get("cover") and (root / ort["cover"]).is_file()), None)
        info = {"tags": tags, "genre": track.get("genre") or "", "url": track.get("permalink_url"),
                "beschreibung": _beschreibung(track.get("description")),
                "cover": cover.replace(chr(92), "/") if cover else None}
        kandidaten = [*eintrag.get("audio_candidates", []), *eintrag.get("musicmaker_audio_candidates", [])]
        if eintrag.get("confirmed_audio"):
            kandidaten.append(eintrag["confirmed_audio"])
        for pfad in kandidaten:
            pfade.setdefault(pfad.replace(chr(92), "/").casefold(), []).append(info)
        for platz in eintrag.get("placements", []):
            ordner = platz["folder"].replace(chr(92), "/").casefold()
            titel.setdefault((ordner, _titel_schluessel(track["title"])), []).append(info)
    album_cover = {eintrag["folder"].replace(chr(92), "/").casefold(): eintrag["cover"].replace(chr(92), "/")
                   for eintrag in daten["local"].get("albums", [])
                   if eintrag.get("cover") and (root / eintrag["cover"]).is_file()}
    return pfade, titel, album_cover


def _release_bilder(ordner):
    bilder = {}
    for datei in sorted(ordner.iterdir()):
        if datei.suffix.lower() not in BILD_EXT or not datei.is_file():
            continue
        stamm = datei.stem.casefold()
        if stamm.startswith("album-cover"):
            bilder.setdefault("", datei.name)
        elif (treffer := re.fullmatch(r"(.+) - cover(?: \[sc \d+\])?", stamm)):
            bilder.setdefault(_titel_schluessel(treffer[1]), datei.name)
    return bilder


def _titelfolge(ordner):
    try:
        zeilen = (ordner / "Album-info.txt").read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return {}
    folge = {}
    for zeile in zeilen:
        if treffer := re.match(r"^\s*(\d{1,3})[.)]\s+(.+?)(?:\s+[—–]\s+.*)?$", zeile):
            folge.setdefault(_titel_schluessel(treffer[2]), int(treffer[1]))
    return folge


class Katalog:
    def __init__(self, cfg):
        self.cfg = cfg
        self.zustand = "leer"  # leer, laeuft, bereit, music_root_missing
        self.gelesen_am = None
        self._dateien = []
        self._alben = []
        self._lock = threading.Lock()
        self._thread = None

    def scan(self):
        root = Path(self.cfg.music_root)
        if not root.is_dir():
            with self._lock:
                self._dateien, self._alben, self.zustand, self.gelesen_am = [], [], "music_root_missing", jetzt()
            return
        dateien = []
        assets = {}
        for ordner, unterordner, namen in os.walk(root):
            unterordner[:] = sorted(n for n in unterordner
                                    if not n.startswith((".", "_")) and n.casefold() not in INTERNE_ORDNER)
            teile = Path(ordner).relative_to(root).parts
            for name in sorted(namen):
                if Path(name).suffix.lower() not in AUDIO_EXT:
                    continue
                pfad = "/".join(teile + (name,))
                _, _, tiefe = ablage(pfad)
                if not tiefe:
                    continue
                unterpfad = teile[tiefe:]
                if "stems" in unterpfad and "premix" not in unterpfad:
                    continue
                basis = "/".join(teile[:tiefe])
                daten = release_metadaten(root, pfad)
                if basis not in assets:
                    ordner_pfad = root / basis
                    assets[basis] = (_release_bilder(ordner_pfad), _titelfolge(ordner_pfad), *_release_texte(ordner_pfad))
                bilder, folge, album_text, song_texte, lyrics = assets[basis]
                song = parse_pfad(pfad, root)
                titel_key = _titel_schluessel(song["titel"])
                bild = bilder.get(titel_key)
                album_bild = bilder.get("")
                dateien.append({"pfad": pfad, **song, "release_pfad": basis,
                                "song_cover": f"{basis}/{bild}" if bild else None,
                                "album_cover": f"{basis}/{album_bild}" if album_bild else None,
                                "track_nummer": folge.get(titel_key), "album_beschreibung": album_text,
                                "song_beschreibung": song_texte.get(titel_key, ""), "lyrics_vorhanden": titel_key in lyrics,
                                "release_titel": daten.get("titel"),
                                "single": ist_single(pfad), "unterordner": "/".join(unterpfad)})
        _e_mastered_zuordnen(dateien)
        sc_pfade, sc_titel, sc_album_cover = _soundcloud_infos(root)
        for datei in dateien:
            links = list(sc_pfade.get(datei["pfad"].casefold(), []))
            links += sc_titel.get((datei["release_pfad"].casefold(), _titel_schluessel(datei["titel"])), [])
            datei["soundcloud"] = links
            datei["album_cover"] = datei["album_cover"] or sc_album_cover.get(datei["release_pfad"].casefold())
        alben = []
        album_ordner = root / "Alben"
        if album_ordner.is_dir():
            for ordner in sorted(album_ordner.iterdir()):
                if not ordner.is_dir() or ordner.name.startswith((".", "_")):
                    continue
                basis = ordner.relative_to(root).as_posix()
                daten = release_metadaten(root, f"{basis}/Album-info.txt")
                bilder = assets[basis][0] if basis in assets else _release_bilder(ordner)
                alben.append({"pfad": basis, "slug": daten.get("slug") or ordner.name,
                              "titel": daten.get("titel") or ordner.name.replace("-", " "),
                              "stilreferenz": daten.get("stilreferenz", ""), "single": False,
                              "cover": f"{basis}/{bilder['']}" if "" in bilder else sc_album_cover.get(basis.casefold()),
                              "beschreibung": assets[basis][2] if basis in assets else _release_texte(ordner)[0]})
        with self._lock:
            self._dateien, self._alben, self.zustand, self.gelesen_am = dateien, alben, "bereit", jetzt()

    def scan_im_hintergrund(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self.zustand = "laeuft"
            self._thread = threading.Thread(target=self.scan, name="katalog-scan", daemon=True)
            self._thread.start()

    def warten(self, timeout=30):
        if self._thread:
            self._thread.join(timeout)

    def zahlen(self):
        with self._lock:
            songs = {(d["release_pfad"], d["titel"]) for d in self._dateien}
            return {"zustand": self.zustand, "dateien": len(self._dateien), "songs": len(songs),
                    "gelesen_am": self.gelesen_am}

    def baum(self, bewertungen, q="", min_score=None):
        """Liefert die Album-/Single-Ansicht sowie die bisherigen nach Stil gruppierten Daten."""
        with self._lock:
            dateien, alben, zustand, gelesen_am = self._dateien, self._alben, self.zustand, self.gelesen_am
        worte = q.lower().split()
        kuenstler, baum, release_baum, anzahl = set(), {}, {}, 0
        for d in dateien:
            if d["artist_slug"]:
                kuenstler.add(d["artist_slug"])
            bewertung = bewertungen.get(d["pfad"])
            if min_score is not None and (bewertung is None or bewertung["score"] < min_score):
                continue
            gruppe = "Singles" if d["single"] else ""
            heuhaufen = f"{d['artist_slug']} {d['release_slug']} {d['release_titel'] or ''} {d['titel']} {gruppe}".lower()
            if any(w not in heuhaufen for w in worte):
                continue
            anzahl += 1
            songs = baum.setdefault(d["artist_slug"], {}).setdefault(d["release_slug"], {})
            datei = {"pfad": d["pfad"], "version": d["version"], "fassung": d["fassung"],
                     "unterordner": d["unterordner"], "bewertung": bewertung}
            songs.setdefault(d["titel"], []).append(datei)
            release = release_baum.setdefault(d["release_pfad"], {
                "pfad": d["release_pfad"], "slug": d["release_slug"],
                "titel": d["release_titel"] or d["release_slug"].replace("-", " "),
                "stilreferenz": d["artist_slug"], "single": d["single"], "songs": {},
                "cover": d["album_cover"], "beschreibung": d["album_beschreibung"],
            })
            song = release["songs"].setdefault(d["titel"], {"titel": d["titel"], "dateien": [],
                "cover": d["song_cover"], "track_nummer": d["track_nummer"], "soundcloud": [],
                "beschreibung": d["song_beschreibung"], "lyrics_vorhanden": d["lyrics_vorhanden"]})
            for info in d["soundcloud"]:
                if info not in song["soundcloud"]:
                    song["soundcloud"].append(info)
            song["dateien"].append(datei)
        artists = []
        for artist in sorted(baum):
            releases = []
            for release in sorted(baum[artist]):
                songs = [{"titel": titel, "dateien": sorted(
                    eintraege, key=lambda e: (e["version"] or 0, e["unterordner"], e["fassung"]))}
                    for titel, eintraege in sorted(baum[artist][release].items())]
                releases.append({"slug": release, "songs": songs})
            artists.append({"slug": artist, "releases": releases})
        mit_audio = {d["release_pfad"] for d in dateien}
        if min_score is None:
            for album in alben:
                if album["pfad"] in mit_audio:
                    continue
                text = f"{album['titel']} {album['slug']} {album['stilreferenz']}".lower()
                if all(wort in text for wort in worte):
                    release_baum[album["pfad"]] = {**album, "songs": {}}
        katalog_releases = []
        for release in sorted(release_baum.values(), key=lambda r: (r["single"], r["titel"].casefold(), r["pfad"])):
            songs = release["songs"].values()
            release["songs"] = sorted(songs, key=lambda song: (song["track_nummer"] or 999, song["titel"].casefold()))
            for song in release["songs"]:
                if len(song["soundcloud"]) == 1:
                    info = song["soundcloud"][0]
                    song["beschreibung"] = song["beschreibung"] or info["beschreibung"]
                    song["cover"] = song["cover"] or info["cover"]
                song["dateien"].sort(key=lambda d: (d["version"] or 0, d["unterordner"], d["fassung"], d["pfad"]))
                song["kurzprofil"] = kurzprofil(release, song)
            katalog_releases.append(release)
        result = {"zustand": zustand, "gelesen_am": gelesen_am, "anzahl_dateien": anzahl,
                  "kuenstler": sorted(kuenstler), "artists": artists, "releases": katalog_releases}
        if zustand == "music_root_missing":
            result.update(error="music_root_missing",
                          meldung=f"Der Musikordner fehlt: {self.cfg.music_root}. „Ich beschreibe es“ geht trotzdem.")
        return result
