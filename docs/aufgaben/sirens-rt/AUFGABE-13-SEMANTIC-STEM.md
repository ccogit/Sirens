# Aufgabe 13: Semantic Stem Extractor (WP13)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP13“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 03 und das Gate G1 für SAM Audio voraus.

## Ziel

Per Textbeschreibung wird eine Quelle aus einem Song gelöst; Ergebnis und Rest liegen als neue Assets vor, mit Vorhören, Abbruch und Cache.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Vor der Vergabe trägt der Koordinator das gemessene Gate G1 und den freigegebenen Modus in `benchmarks/spikes/README.md` ein. Diese Aufgabe setzt genau diesen Modus um; bei „rot“ entfällt sie.
- Bericht: `benchmarks/spikes/sam_audio/`. Cache-Muster aus Aufgabe 08, falls gemergt.

## Umfang

1. `workers/sam_audio/` mit Manifest, Adapter, Lockfile, `install.ps1`; Modellgröße passend zu 16 GB, sonst kürzere Segmente oder Offline.
2. Job mit Textprompt; isolierte Quelle und Rest als Assets, ausgerichtet auf das Original; Cache.
3. Messskript `benchmarks/semantic/`: fünf Beschreibungen auf lokalen Tracks.

## Nicht im Umfang

- Keine Übertragung von Musik ins Netz.
- Kein Versprechen perfekter Trennung.

## Abnahme

1. Tests mit nachgebautem Modell: Job-Lebenszyklus, Abbruch, Cache, Quelle plus Rest ergibt das Original (Toleranz angegeben), Fähigkeit nur sichtbar bei installierter Version.
2. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: fünf Beschreibungen, qualitativer Bericht.
3. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
