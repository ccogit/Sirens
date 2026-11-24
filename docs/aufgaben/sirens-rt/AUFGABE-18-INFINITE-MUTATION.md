# Aufgabe 18: Infinite Mutation und automatisierte Performance (WP18, optional)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP18“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt die Aufgaben 10, 14 und 16 sowie mindestens einen freigegebenen neuronalen Pfad (Aufgabe 07 oder 11) voraus.

## Ziel

Ein Mix verändert sich über 4, 8 oder 16 Takte von selbst, kontrolliert und wiederholbar, mit jederzeit möglicher Rückkehr zum Original.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Scheduler und Effekte aus den Aufgaben 09, 12 und 14; Session-Protokoll aus Aufgabe 16.

## Umfang

1. `web/js/realtime/mutation_scheduler.js` (reine Logik): Automation über Taktblöcke, Intensität, Energie-Regie, Wiederholbarkeit über Seed, Übersteuern von Hand, Rückkehr zum Original.
2. Grenzen für Lautheit, Warteschlange, Modellwechsel und erzeugte Assets (Quota); Protokoll in der Session.
3. Ohne neuronalen Pfad: DSP-Modus, ausdrücklich als reduziert benannt.
4. Messskript `benchmarks/mutation/`: 30 Minuten, drei Szenarien.

## Nicht im Umfang

- Keine ungeprüften Modellwechsel.
- Keine endlose Asset-Erzeugung.

## Abnahme

1. Node-Tests: gleicher Seed → gleiche Folge; Wechsel nur an Taktgrenzen; Quota und Lautheitsgrenze greifen; Stop und Original jederzeit.
2. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: 30 Minuten Lauf.
3. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
