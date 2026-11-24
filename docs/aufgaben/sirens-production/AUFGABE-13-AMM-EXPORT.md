# Aufgabe 13 – Kette KETTE-P12, Aufgabe 1 von 3. AMM-Export als Befehl

Folgeaufgabe aus dem ersten echten Clear-Head-Lauf am Zielrechner (Windows 11, RTX 5080, py -3.11), 24.11.2026. Lies PLAN.md, CONTRACT.md, KETTEN.md (Begriffe, Regeln) und die genannte Ergebnisdatei. Kein Test braucht Netz, GPU, Plugins oder Live; Tests müssen unter Linux UND Windows laufen.

Dateien: `sirens/production/references.py` (neue Funktion/Unterbefehl), Tests `tests/production/test_references*`.

## Befund
Für echte Prompts/Lyrics/Bewertungen musste der Koordinator die Exportprojektion (Format in `ergebnisse/K01.md`) per Hand aus der AMM-PostgreSQL bauen: lesend über `music_generation_jobs.local_file_path` → Paket → Song → Release/Artist, Pfadzerlegung mit Sirens' `parse_pfad`, neuestes Paket je Identität gewinnt, Bewertungen hängen nur auf Song-Ebene. 1477 Pfade beginnen mit `.\generated-music\`.

## Umfang
1. `python -m sirens.production.references amm-export --out <datei>`: liest aus einer lokalen JSON-Zeilendatei oder (optional) über einen konfigurierten lesenden DB-Befehl; keine SQL-Freitexte aus Eingaben, nur lesend (`BEGIN READ ONLY`), keine Zugangsdaten in Ausgaben/Logs.
2. Pfad-Präfixe normalisieren (`.\generated-music\`), neuestes Paket je Identität, Song-Bewertungen als solche markieren (nicht je Version doppelt zählen).

## Abnahme
Tests mit Fixture-Zeilen (Dubletten, Präfixe, fehlende Dateien, Song-Bewertung über mehrere Versionen).
