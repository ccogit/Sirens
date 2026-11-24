# Aufgabe 10: BeatGrid, Tonart, MIDI (WP10)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Kapitel 4 („Zeitbasis“) und Abschnitt „WP10“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 01 voraus.

## Ziel

Ein einheitliches BeatGrid für alle Folgemodule: Tempo, Schläge, Taktanfänge mit Konfidenz, korrigierbar von Hand. Dazu Tonart und Noten als Zusatz, ohne falsche Sicherheit.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- `sirens/beat.py`: Schätzung von Tempo und Schlägen (liest über `ffmpeg`). `sirens/dramaturgie.py`: Phrasen und Abschnitte. `sirens/stem_notes.py`, `sirens/stem_transcribe.py`: Noten über Basic Pitch in eigener Umgebung. Tests: `tests/test_beat.py`. Diese Module bleiben in ihrem Verhalten gleich.
- Klickspuren mit bekannter Wahrheit: `benchmarks/fixtures.py`.

## Umfang

1. `sirens/realtime/music_analysis.py`: baut aus `beat.py`/`dramaturgie.py` ein BeatGrid nach dem Schema aus Aufgabe 01 (BPM, `beat0`, `bar0`, Konfidenz, optionale Tempo-Karte); Korrekturen: halbes/doppeltes Tempo, Taktanfang verschieben, Phasenversatz, Tap-Tempo; Korrekturen werden je Quell-Hash gespeichert.
2. Tonart über Chroma (nur Standardbibliothek oder im Worker); bei geringer Konfidenz „unsicher“ statt einer Tonart.
3. `web/js/realtime/beat_grid.js`: reine Funktionen (Frame ↔ Schlag ↔ Takt, nächste Taktgrenze, Quantisierung), unter Node testbar.
4. Option für ein Modell (z. B. Beat This! Live) nur als Worker-Manifest und Adapter-Stub nach dem Bericht aus Aufgabe 02, abgeschaltet bis zur Messung.
5. Adresse `GET /api/rt/v1/...` für das BeatGrid als Hook `docs/realtime/hooks/WP10.md`; Messskript `benchmarks/beatgrid/` für echte Tracks mit Referenz aus dem lokalen Manifest.

## Nicht im Umfang

- Keine Änderung am Verhalten von `sirens/beat.py` und `sirens/dramaturgie.py`.
- Kein Modell-Download.

## Abnahme

1. Tests mit Klickspuren 120, 140, 150 BPM: Tempo stimmt, Schläge und Taktanfänge nach der Einrastphase höchstens 20 ms daneben.
2. Tests: jede Korrektur (halb/doppelt, Taktanfang, Phase, Tap) wirkt und bleibt gespeichert; Stille oder Rauschen ergibt geringe Konfidenz und keinen erfundenen Wert; Tonart „unsicher“ bei tonlosem Signal.
3. Node-Tests zu `beat_grid.js`: Umrechnungen und Quantisierung auf das Sample, auch mit Tempo-Karte.
4. `tests/test_beat.py` unverändert grün.
5. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: echte Tracks mit Referenz.
6. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
