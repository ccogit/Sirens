# Aufgabe 15: Generative Companion (WP15, optional)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP15“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt die Aufgaben 06 und 10 und das Gate G1 für Magenta RealTime voraus.

## Ziel

Eine zusätzliche, lokal erzeugte Begleitspur, steuerbar über Text, MIDI oder Stilreferenz, mit eigenem Pegel und sauberem Stop.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Vor der Vergabe trägt der Koordinator das gemessene Gate G1 und den freigegebenen Modus in `benchmarks/spikes/README.md` ein. Diese Aufgabe setzt genau diesen Modus um; bei „rot“ entfällt sie.
- Bericht: `benchmarks/spikes/magenta/`.

## Umfang

1. `workers/magenta/` mit Manifest, Adapter, Lockfile, `install.ps1` (bei Bedarf WSL2, dokumentiert).
2. Begleitspur als eigene Spur im Audio-Kern; Regler für Pegel, Stil, MIDI; Stop und Bypass.
3. Messskript `benchmarks/companion/`: 10 Minuten, Ressourcenbericht.

## Nicht im Umfang

- Keine behauptete Beatbindung ohne Nachweis.

## Abnahme

1. Tests mit nachgebautem Modell: Lebenszyklus, Stop/Bypass, Regler wirken.
2. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: 10 Minuten echte Begleitspur.
3. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
