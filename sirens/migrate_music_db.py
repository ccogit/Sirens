"""Optionale Pfadaktualisierung in einer lokalen Musicmaker-PostgreSQL-Instanz."""
import json
import subprocess

SPALTEN = {
    "music_generation_jobs": ("local_file_path",),
    "music_masters": ("source_file_path", "output_file_path"),
    "music_wav_conversions": ("local_file_path",),
    "genaudio_runs": ("audio_path",),
}


class MusicmakerPfade:
    def __init__(self, container):
        self.befehl = ["podman", "exec", "-i", "-e", "PGCLIENTENCODING=UTF8", container,
                       "psql", "-X", "-U", "musicmaker", "-d", "musicmaker", "-At", "-v", "ON_ERROR_STOP=1"]

    def sql(self, sql):
        lauf = subprocess.run(self.befehl, input=sql.encode("utf-8"), capture_output=True, check=False)
        if lauf.returncode:
            raise RuntimeError(lauf.stderr.decode("utf-8", errors="replace").strip())
        return lauf.stdout.decode("utf-8")

    def planen(self, ersetzen):
        aenderungen = {}
        for tabelle, spalten in SPALTEN.items():
            for spalte in spalten:
                antwort = self.sql(f"SELECT COALESCE(json_agg(json_build_array(id, {spalte})), '[]') "
                                   f"FROM {tabelle} WHERE {spalte} IS NOT NULL;")
                neu = []
                for id_, alt in json.loads(antwort):
                    pfad = ";".join(ersetzen(wert) for wert in alt.split(";"))
                    if pfad != alt:
                        neu.append({"id": id_, "alt": alt, "neu": pfad})
                if neu:
                    aenderungen[(tabelle, spalte)] = neu
        return aenderungen

    def anwenden(self, aenderungen):
        befehle = ["BEGIN;", "SET LOCAL standard_conforming_strings = on;"]
        for (tabelle, spalte), zeilen in aenderungen.items():
            daten = json.dumps(zeilen, ensure_ascii=False).replace("'", "''")
            befehle.append(f"""
CREATE TEMP TABLE pfade_tmp ON COMMIT DROP AS
SELECT * FROM jsonb_to_recordset('{daten}'::jsonb) AS x(id bigint, alt text, neu text);
WITH geaendert AS (
    UPDATE {tabelle} AS eintrag SET {spalte} = x.neu
    FROM pfade_tmp AS x
    WHERE eintrag.id = x.id AND eintrag.{spalte} = x.alt
    RETURNING eintrag.id
)
SELECT 1 / ((SELECT count(*) FROM geaendert) = (SELECT count(*) FROM pfade_tmp))::int;
DROP TABLE pfade_tmp;""")
        self.sql("\n".join([*befehle, "COMMIT;"]))
