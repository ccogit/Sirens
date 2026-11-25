# Aufgabe 31: DSP-Steuerlatenz messen und senken

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt die gemergten
Aufgaben 09 und 17/26 voraus. Folgeaufgabe aus der Systemabnahme G4 (Aufgabe 19).

## Ziel

Ein Regler im DSP-Rack wirkt hörbar innerhalb des G3-Ziels von 50 ms (p95), und die Messung trennt die
Gerätelatenz sauber von der Latenz, die Sirens verursacht.

## Ausgangslage

- G4-Messung (WP09, Profil fast, 1 Stem, RTX 5080, Windows): Control-to-Audio p50 79,7 ms, p95 82,7 ms,
  p99 83,3 ms. Das Ziel ≤ 50 ms ist verfehlt. Die Werte sind eine Schätzung aus dem Ausgabezeitstempel.
- Messung: `benchmarks/dsp/browser.js` (`control_ms` = gehört − ausgelöst; `output_latency_ms` aus
  `context.outputLatency` wird nur mitgeschrieben, nicht abgezogen), Auswertung `benchmarks/dsp/report.py`.
- DSP-Pfad: `web/js/realtime/effects/` (Rack, Parameter-Glättung, Presets). `audio_core.js` setzt
  `dspLatency=896` Frames (≈ 18,7 ms bei 48 kHz). Die Steuerbefehle gehen als `dspParam` an den Worklet
  (`web/js/realtime/worklet_processor.js`).

## Umfang

1. Messung zerlegen: Gerätelatenz (`outputLatency`, `baseLatency`), Rack-Latenz, Glättungs- bzw. Rampenzeit
   und Weg der Nachricht. Die Kennzahl für G3 ist die Sirens-eigene Latenz ohne Gerätelatenz. Die
   Gesamtlatenz wird zusätzlich ausgewiesen.
2. Die größten Anteile senken, z. B. kürzere Parameter-Rampen für Steuerbewegungen, Lookahead nur dort, wo er
   nötig ist, Profil fast mit kleinerem Block. Die Klangqualität bleibt erhalten: keine Klicks bei
   Sprüngen, das muss als Test nachweisbar sein.
3. Änderungen am Worklet nur, wenn unvermeidbar, und dann nur im Teil für `dspParam`/`dspPreset`. Der
   Loop-/Epoch-Teil gehört Aufgabe 30.

## Nicht im Umfang

- Loop- und Epoch-Wechsel (Aufgabe 30), Mess-Harness Recorder/Audio Core/Suite (Aufgabe 32).

## Abnahme

1. Offline-Test (Node, Rack mit Impuls): Die Zeit vom Parameterwechsel bis 90 % der Zielwirkung liegt im
   Profil fast unter 30 ms bei 48 kHz. Es entsteht kein Klick, gemessen als Sprung im Ausgangssignal
   unter einer festgelegten Schwelle.
2. `benchmarks/dsp/report.py` gibt Sirens-Latenz und Gesamtlatenz getrennt aus und hat einen Test mit
   nachgebauten Messdaten.
3. Alle bestehenden Tests bleiben grün.
4. Ergebnisdatei `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-31.md` mit Zerlegung vorher/nachher (aus
   Offline-Test) und dem Befehl für die Browser-Messung. Die Messung auf der Hardware führt der
   Koordinator aus.
