# Aufgabe 12: Generative Performance Pads (WP12)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP12“ und Kapitel 7 (G3 Lookahead) in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt die Aufgaben 06 und 10 und das Gate G1 für Stable Audio voraus.

## Ziel

Pads lösen musikalische Aktionen aus (Rise, Fill, Drop, Break, Bassline, Extend): Ein Job erzeugt Audio vorab, der Scheduler setzt es taktgenau ein oder verschiebt es; nie mitten in der Phrase.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Vor der Vergabe trägt der Koordinator das gemessene Gate G1 und den freigegebenen Modus in `benchmarks/spikes/README.md` ein. Diese Aufgabe setzt genau diesen Modus um; bei „rot“ entfällt sie.
- BeatGrid: `sirens/realtime/music_analysis.py`, `web/js/realtime/beat_grid.js`. Bericht: `benchmarks/spikes/` (Stable Audio).

## Umfang

1. `workers/stable_audio/`: jobbasierter Adapter (Prompt, Seed, Stärke, Länge 1/2/4/8 Takte); Inpainting oder Fortsetzung nur, wenn das Modell es kann.
2. `web/js/realtime/pad_scheduler.js` (reine Logik): Vorlauf aus gemessener p95-Renderzeit, Frist je Job, Vorhören, Einsatz mit Crossfade, Verschieben auf den nächsten geeigneten Takt oder Dry, begrenztes Stretching mit Warnung, begrenzte Warteschlange.
3. Messskript `benchmarks/pads/`: 20 Jobs, Quote rechtzeitiger Einsätze.

## Nicht im Umfang

- Kein DEMON-Backend, solange Aufgabe 07 nicht gemergt ist.

## Abnahme

1. Node-Tests zum Scheduler mit nachgebauter Renderzeit: rechtzeitig → Einsatz auf das Sample an der Taktgrenze; verspätet → verschoben oder verworfen, nie erzwungen; Warteschlange wächst nicht über die Grenze; mindestens drei Pad-Typen.
2. Negativ: BeatGrid mit geringer Konfidenz → kein automatischer Einsatz.
3. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: 20 echte Jobs, Ziel mindestens 95 % rechtzeitig.
4. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
