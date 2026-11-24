"""Aktualisiert öffentliche SoundCloud-Zahlen in Musicmaker über das Eigentümerkonto."""
import argparse
import contextlib
import importlib.util
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .migrate_music_db import MusicmakerPfade


def zugang(upload_skript):
    spec = importlib.util.spec_from_file_location("soundcloud_upload", upload_skript)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    with contextlib.redirect_stdout(io.StringIO()):
        return modul.get_access_token(modul.load_env())


def abrufen(upload_skript, profil):
    import requests

    kopf = {"Authorization": "OAuth " + zugang(upload_skript)}
    basis = "https://api.soundcloud.com"
    konto = requests.get(basis + "/me", headers=kopf, timeout=25)
    konto.raise_for_status()
    if konto.json().get("permalink") != profil:
        raise RuntimeError("Angemeldetes SoundCloud-Konto stimmt nicht mit dem gewünschten Profil überein.")
    url = basis + "/me/tracks?linked_partitioning=true&limit=200"
    gesehen = set()
    verfuegbare = []
    while url:
        quelle = urlparse(url)
        if quelle.scheme != "https" or quelle.netloc != "api.soundcloud.com" or url in gesehen:
            raise RuntimeError("Ungültige SoundCloud-Paginierung.")
        gesehen.add(url)
        antwort = requests.get(url, headers=kopf, timeout=35)
        antwort.raise_for_status()
        seite = antwort.json()
        verfuegbare.extend(seite["collection"])
        url = seite.get("next_href")
    auswahl = {}
    felder = ("title", "permalink_url", "playback_count", "likes_count", "comment_count", "reposts_count", "download_count")
    for t in verfuegbare:
        if t.get("sharing") != "public":
            continue
        track_id = t.get("id") or str(t["urn"]).split(":")[-1]
        auswahl[int(track_id)] = {"id": int(track_id), **{f: t.get(f) for f in felder}}
    if not auswahl:
        raise RuntimeError("SoundCloud meldet keine öffentlichen Tracks.")
    return list(auswahl.values())


def speichern(db, profil, tracks):
    daten = json.dumps(tracks, ensure_ascii=False).replace("'", "''")
    profil = profil.replace("'", "''")
    zeit = datetime.now(timezone.utc).isoformat()
    db.sql(f"""
BEGIN;
SET LOCAL standard_conforming_strings = on;
INSERT INTO soundcloud_track_observations
SELECT id, '{profil}', title, permalink_url, playback_count, likes_count, comment_count, reposts_count, download_count, '{zeit}'
FROM jsonb_to_recordset('{daten}'::jsonb) AS x(id bigint,title text,permalink_url text,playback_count bigint,
   likes_count bigint,comment_count bigint,reposts_count bigint,download_count bigint)
ON CONFLICT (track_id) DO UPDATE
SET title=excluded.title, url=excluded.url,
    plays=COALESCE(excluded.plays,soundcloud_track_observations.plays),
    likes=COALESCE(excluded.likes,soundcloud_track_observations.likes),
    comments=COALESCE(excluded.comments,soundcloud_track_observations.comments),
    reposts=COALESCE(excluded.reposts,soundcloud_track_observations.reposts),
    downloads=COALESCE(excluded.downloads,soundcloud_track_observations.downloads),
    observed_at=excluded.observed_at
WHERE soundcloud_track_observations.observed_at <= excluded.observed_at;
COMMIT;""")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upload_skript", type=Path)
    parser.add_argument("--profil", default="cco_music")
    parser.add_argument("--container", default="musicmaker-postgres")
    args = parser.parse_args()
    tracks = abrufen(args.upload_skript, args.profil)
    speichern(MusicmakerPfade(args.container), args.profil, tracks)
    print(f"Öffentliche SoundCloud-Tracks aktualisiert: {len(tracks)}")


if __name__ == "__main__":
    main()
