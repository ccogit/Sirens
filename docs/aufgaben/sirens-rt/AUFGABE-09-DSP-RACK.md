# Aufgabe 09: DSP Rack: Spektral, Granular, Faltung (WP09)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP09“ und Kapitel 7 (G3 Fast DSP) in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt die Aufgaben 02 und 04 voraus.

## Ziel

Ein Effekt-Rack mit mindestens drei hörbar nutzbaren Familien als stabile CPU-Referenz im Browser (JavaScript, wo nötig WASM): spektrales Freeze/Masking/Pitch, granulares Stretch/Cloud, partitionierte Faltung mit IR-Morphing. Ein GPU-Backend kommt nur dazu, wenn eine Messung den Vorteil belegt.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Audio-Kern aus Aufgabe 04: `web/js/realtime/audio_core.js`, `worklet_processor.js`.
- Bericht zum GPU Audio SDK und zu Signalsmith Stretch: `benchmarks/spikes/`.

## Umfang

1. `web/js/realtime/effects/`: gemeinsame Effekt-Schnittstelle (Parameter mit Glättung, Wet/Dry, Bypass, deklarierte Latenz in Frames, Presets), je Familie ein Modul, reine Rechenkerne ohne DOM.
2. Spektral: STFT mit Overlap-Add, Freeze, Maskierung, Pitch. Granular: Time Stretch und Cloud. Faltung: partitioniert, Morphing zwischen zwei Impulsantworten (erzeugte IRs, keine fremden Dateien).
3. Profile für FFT-Größe, Korngröße, IR-Länge. Einbindung in den Audio-Kern als Kette mit Latenzausgleich; Einbau in die Oberfläche als Hook `docs/realtime/hooks/WP09.md`.
4. Messskript `benchmarks/dsp/`: gleiche Signalpfade, Zusatzlatenz, Control-to-audio, mehrere Stems und Effekte parallel; vorbereitet für einen späteren Vergleich CPU gegen GPU.
5. `native/gpu_dsp/` nur als ADR mit Plan, falls der Bericht das SDK für geeignet hält; kein Code ohne Messung.

## Nicht im Umfang

- Kein GPU-Code ohne belegten Vorteil.
- Keine Änderung am Audio-Kern außer über seine Schnittstelle.

## Abnahme

1. Node-Tests je Effekt mit Impuls, Sinus und Stereo: kein NaN/Inf, Bypass bitgleich, Wet 0 bitgleich nach Latenzausgleich, deklarierte Latenz stimmt auf das Sample, Parameterwechsel ohne Sprung (Glättung), Energie bleibt in Grenzen.
2. Tests: Pitch um eine Oktave verdoppelt die Frequenz eines Sinus (Toleranz angegeben); Stretch um Faktor 2 verdoppelt die Dauer bei gleicher Tonhöhe; Faltung mit Impuls ergibt die IR.
3. Negativ: ungültige Parameter werden begrenzt oder abgelehnt.
4. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft Gate G3: Zusatzlatenz und Control-to-audio am Zielrechner.
5. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
