# Aufgabe 08: Advanced Stem Studio (WP08)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP08“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 03 und das Gate G1 für die Trennmodelle voraus.

## Ziel

Neben Demucs stehen weitere Trennmodelle (RoFormer, DrumSep) zur Wahl, mit modellabhängigen Stem-Listen, Cache und ehrlicher Kennzeichnung. Das bestehende Stem Studio funktioniert unverändert weiter.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Vor der Vergabe trägt der Koordinator das gemessene Gate G1 und den freigegebenen Modus in `benchmarks/spikes/README.md` ein. Diese Aufgabe setzt genau diesen Modus um; bei „rot“ entfällt sie.
- `sirens/stems.py`: Demucs als Unterprozess, WAV-Cache, Adressen `/api/stems`. `sirens/stem_notes.py`: Notenerkennung. `web/js/stems.js`, `web/js/stem_audio.js`: Oberfläche und Player. Tests: `tests/test_stems.py`. Bericht: `benchmarks/spikes/` (RoFormer/DrumSep).

## Umfang

1. `workers/separation/` mit Manifesten je Modell; `sirens/realtime/stem_adapter.py` mit Registry für Demucs, RoFormer, DrumSep. Die bestehende API in `sirens/stems.py` bleibt gleich.
2. Cache-Schlüssel aus Quell-Hash, Modellrevision und Parametern; atomares Veröffentlichen; Wiederverwendung.
3. Stem-Listen kommen vom Modell; Kick/Snare/Hi-Hat nur, wenn das Modell sie liefert.
4. Oberfläche als eigenes Modul unter `web/js/realtime/` (A/B, Solo/Mute, Gain, Export außerhalb des Originalordners); Einbau als Hook `docs/realtime/hooks/WP08.md`.
5. Messskript `benchmarks/separation/`: Rekonstruktion (Summe der Stems gegen Original), Übersprechen mit geeigneten Fixtures, Ausrichtung.

## Nicht im Umfang

- Keine Änderung an bestehenden Adressen von `sirens/stems.py`.
- Kein Streaming-Versprechen ohne Messung.

## Abnahme

1. Tests mit nachgebautem Trenner: Cache-Treffer bei gleichem Schlüssel, neuer Lauf bei anderer Revision, atomares Veröffentlichen (abgebrochener Lauf hinterlässt nichts), Ausrichtung der Stems auf das Sample, Rückfall auf Demucs bei Fehler.
2. Negativ: Modell ohne Drum-Spuren bietet keine an; unbekanntes Modell → `invalid`.
3. `tests/test_stems.py` unverändert grün.
4. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: echtes alternatives Modell, Qualitätsbericht.
5. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
