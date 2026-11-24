# Aufgabe 11: Neural Mutation und Audio Fusion: RAVE, AFTER (WP11)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP11“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 06 und das Gate G1 für RAVE bzw. AFTER voraus.

## Ziel

Klangveränderung über latente Räume: RAVE-Latent-Regler, Morphing, taktgebundener Random-Walk, AFTER mit Struktur- und Klangfarben-Referenz; je Modell getrennt freigeschaltet und im gemessenen Modus.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Vor der Vergabe trägt der Koordinator das gemessene Gate G1 und den freigegebenen Modus in `benchmarks/spikes/README.md` ein. Diese Aufgabe setzt genau diesen Modus um; bei „rot“ entfällt sie.
- Berichte: `benchmarks/spikes/rave/`, `benchmarks/spikes/after/`. Muster: `workers/mock/`.

## Umfang

1. `workers/rave/` und `workers/after/` mit Manifest, Adapter, Lockfile, `install.ps1`; nur vortrainierte Modelle mit geprüfter Lizenz.
2. Regler aus dem Descriptor; reproduzierbare Presets (Seed, Parameter); Wet/Dry.
3. Messskript `benchmarks/neural_mutation/`: drei Klangveränderungen je Modell, Latenz, 30 Minuten bei Streaming.
4. Eigenes Training nur als Dokument mit getrenntem GPU-Profil, kein Code.

## Nicht im Umfang

- Kein Streaming-Kennzeichen ohne gemessene Latenz und Kontext.

## Abnahme

1. Tests mit nachgebautem Modell: Lebenszyklus, Presets reproduzierbar, Random-Walk wechselt nur an Taktgrenzen (BeatGrid), Abbruch.
2. Negativ: fehlende Gewichte → `unavailable`.
3. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: echte Klangveränderungen, Latenzbericht.
4. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
