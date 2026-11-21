"""Referenzkatalog: liest den Musikordner (nur lesend) und zeigt die beste bekannte Bewertung je Datei."""
import json
import os
import threading
from pathlib import Path

from .contracts import AUDIO_EXT, parse_pfad
from .store import jetzt

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


class Katalog:
    def __init__(self, cfg):
        self.cfg = cfg
        self.zustand = "leer"  # leer, laeuft, bereit, music_root_missing
        self.gelesen_am = None
        self._dateien = []
        self._lock = threading.Lock()
        self._thread = None

    def scan(self):
        root = Path(self.cfg.music_root)
        if not root.is_dir():
            with self._lock:
                self._dateien, self.zustand, self.gelesen_am = [], "music_root_missing", jetzt()
            return
        dateien = []
        for ordner, unterordner, namen in os.walk(root):
            unterordner.sort()
            teile = Path(ordner).relative_to(root).parts
            if len(teile) < 2:  # erst ab Künstler/Release
                continue
            for name in sorted(namen):
                if os.path.splitext(name)[1].lower() in AUDIO_EXT:
                    pfad = "/".join(teile + (name,))
                    dateien.append({"pfad": pfad, **parse_pfad(pfad), "unterordner": "/".join(teile[2:])})
        with self._lock:
            self._dateien, self.zustand, self.gelesen_am = dateien, "bereit", jetzt()

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
            songs = {(d["artist_slug"], d["release_slug"], d["titel"]) for d in self._dateien}
            return {"zustand": self.zustand, "dateien": len(self._dateien), "songs": len(songs),
                    "gelesen_am": self.gelesen_am}

    def baum(self, bewertungen, q="", min_score=None):
        """Künstler → Releases → Songs → Dateien. `q`: alle Wörter müssen in Künstler, Release oder Titel vorkommen."""
        with self._lock:
            dateien, zustand = list(self._dateien), self.zustand
        worte = q.lower().split()
        kuenstler, baum, anzahl = [], {}, 0
        for d in dateien:
            if d["artist_slug"] not in kuenstler:
                kuenstler.append(d["artist_slug"])
            bewertung = bewertungen.get(d["pfad"])
            if min_score is not None and (bewertung is None or bewertung["score"] < min_score):
                continue
            heuhaufen = f"{d['artist_slug']} {d['release_slug']} {d['titel']}".lower()
            if any(w not in heuhaufen for w in worte):
                continue
            anzahl += 1
            songs = baum.setdefault(d["artist_slug"], {}).setdefault(d["release_slug"], {})
            songs.setdefault(d["titel"], []).append({
                "pfad": d["pfad"], "version": d["version"], "fassung": d["fassung"],
                "unterordner": d["unterordner"], "bewertung": bewertung})
        artists = []
        for artist in sorted(baum):
            releases = []
            for release in sorted(baum[artist]):
                songs = [{"titel": titel, "dateien": sorted(
                    eintraege, key=lambda e: (e["version"] or 0, e["unterordner"], e["fassung"]))}
                    for titel, eintraege in sorted(baum[artist][release].items())]
                releases.append({"slug": release, "songs": songs})
            artists.append({"slug": artist, "releases": releases})
        result = {"zustand": zustand, "gelesen_am": self.gelesen_am, "anzahl_dateien": anzahl,
                  "kuenstler": sorted(kuenstler), "artists": artists}
        if zustand == "music_root_missing":
            result.update(error="music_root_missing",
                          meldung=f"Der Musikordner fehlt: {self.cfg.music_root}. „Ich beschreibe es“ geht trotzdem.")
        return result
