# Aufgabe 07: DEMON Neural Remix Deck (WP07)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP07“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 06 und das Gate G1 für DEMON voraus.

## Ziel

Ein Song lässt sich im RTX Neural Lab mit DEMON hörbar und steuerbar verwandeln (Prompt, Stärke, Seed, Stil-Mischung), im gemessenen Modus und mit sauberem Rückfall auf Dry.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Vor der Vergabe trägt der Koordinator das gemessene Gate G1 und den freigegebenen Modus in `benchmarks/spikes/README.md` ein. Diese Aufgabe setzt genau diesen Modus um; bei „rot“ entfällt sie.
- Bericht und Messskript: `benchmarks/spikes/demon/`. Mock-Worker als Muster: `workers/mock/`.

## Umfang

1. `workers/demon/`: Worker mit eigener Umgebung und Lockfile, `manifest.json` mit Capability-Descriptor, Adapter nach `docs/realtime/model-adapter.md`; optional lokaler TensorRT-Engine-Bau als eigenes Skript.
2. Bedienelemente entstehen aus dem Descriptor; nur Parameter, die das Modell wirklich hat. Wechsel von Quelle und Prompt sind versioniert (Epoch). Verzögerung wird ausgeglichen.
3. Installation `workers/demon/install.ps1` nach dem Muster der Spikes (kein Download ohne Zustimmung).
4. Messskript `benchmarks/demon/`: drei verschiedene Transformationen, 30 Minuten Lauf, bei Lookahead die Quote rechtzeitiger Einsätze.

## Nicht im Umfang

- Kein Torch im Hauptprozess.
- Keine Fähigkeit anzeigen, die nicht gemessen ist.

## Abnahme

1. Tests mit nachgebautem Modell (gleiche Schnittstelle, keine Gewichte): Adapter-Lebenszyklus, Abbruch, Quellenwechsel, Bypass, Fehler beim Laden → Fähigkeit abgeschaltet.
2. Negativ: fehlende Umgebung oder Gewichte → `unavailable` mit Installationshinweis.
3. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: echter Ton aus eigenem Song, drei Transformationen, 30 Minuten, Gate G3.
4. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
