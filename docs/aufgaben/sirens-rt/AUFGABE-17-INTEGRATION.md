# Aufgabe 17: Produktintegration und UX (WP17)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP17“ und Kapitel 7 (Gate G3) in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt die Aufgaben 08, 09, 14 und 16 sowie die freigegebenen optionalen Aufgaben voraus.

## Ziel

Alle freigegebenen Module hängen im Live Lab zu einer Performance-Suite zusammen: durchgehende Abläufe vom Laden bis zum Export, GPU-Profile, Presets, Panic, Automation, klare Kennzeichnung von Modell und Modus.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Alle Hooks unter `docs/realtime/hooks/`. Stand der Freigaben: `docs/realtime/board.md` und `benchmarks/spikes/README.md`. Bestehende CUDA-Sperre beim Claude-Start in `sirens/server.py`.

## Umfang

1. Alle offenen Hooks einbauen. Diese Aufgabe darf alle gemeinsamen Dateien ändern (README, Abschnitt 4, Punkt 7).
2. Durchgehender Ablauf: Song laden, Stems wählen, Effekt oder KI einschalten, Pad auslösen, aufnehmen, exportieren, stoppen. Such- und Katalogzugriff, Preset-System, Parameter-Automation, optionale MIDI-Zuordnung, Diagnose- und Installationsseite.
3. Globale GPU-Regel: Der GPU-Manager ersetzt die alte CUDA-Sperre beim Claude-Start; Visualisierung drosselt im Neural-Profil zuerst. Ohne Telemetrie gilt weiter die konservative Sperre.
4. Nur freigegebene Fähigkeiten erscheinen als nutzbar; abgeschaltete Modelle blockieren nichts.

## Nicht im Umfang

- Keine neuen Modelle.
- Keine versteckten Downloads.

## Abnahme

1. Tests über HTTP und Node für den durchgehenden Ablauf mit Mock: jeder Schritt, Panic, Verlassen ohne Leck (Timer, AudioContext, Worker).
2. Tests: Claude-Start während laufender Sitzung folgt der GPU-Regel; ohne Telemetrie konservativ.
3. Negativ: nicht freigegebenes Modell ist abgeschaltet und benannt; Schalter aus → Bestand unverändert.
4. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft Gate G3 je Funktion und die Sichtprüfung der Abläufe.
5. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
