# Aufgabe 14: Performance-Tools: Drum Architect, Stem Crossover, Acid Transformer (WP14)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP14“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt die Aufgaben 06, 08, 09 und 10 voraus.

## Ziel

Drei musikalische Werkzeuge auf Basis von Stems, BeatGrid und Effekt-Rack: Schlagzeug ersetzen oder doppeln, Stems aus bis zu vier Songs kreuzen, aus der Basslinie einen Acid-Synth erzeugen.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Stems: `sirens/realtime/stem_adapter.py`; Effekte: `web/js/realtime/effects/`; BeatGrid: `web/js/realtime/beat_grid.js`; Synth-Vorbild: `web/js/stem_synth.js`; Noten: `sirens/stem_notes.py`; Kick-Tausch-Vorbild: `sirens/kicktausch.py`, `sirens/kick_dsp.py`.

## Umfang

1. `web/js/realtime/drum_architect.js`: Kick/Snare/Becken ersetzen oder doppeln, Groove, Onsets und Velocity erhalten, Korrektur von Hand; ohne Drum-Stems nur vorhandene Spuren.
2. `web/js/realtime/stem_crossover.js`: bis zu vier Songs, Beat- und Tonart-Abgleich, begrenztes Stretching, Pegelangleich, Konfliktwarnung, Quantisierung.
3. `web/js/realtime/acid_transformer.js`: aus Bass-Noten oder Onsets ein resonanter Synth mit Akzent, Slide, Filter, Drive, Oktave; Bassspur wahlweise ausblenden.
4. Gemeinsame Scheduler- und Effekt-Schnittstelle; Presets; Einbau als Hook `docs/realtime/hooks/WP14.md`; je Werkzeug drei nachstellbare Demos aus Fixtures.

## Nicht im Umfang

- Kein Anspruch auf perfekte harmonische Automatik.

## Abnahme

1. Node-Tests je Werkzeug mit Fixtures: Einsätze auf das Sample am Raster, keine Drift über 10 Minuten (gerechnet), Pegel in Grenzen, Play/Stop/Seek, Presets vollständig speicher- und ladbar.
2. Negativ: fehlende Drum-Stems, Tonartkonflikt, zu starkes Stretching → Warnung statt stiller Fehler.
3. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: Hörprüfung der Demos.
4. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
