# WP04 – Browser-Messung (kein Modell)
1. Vom Repository-Wurzelordner: `python -m benchmarks.audio_core.serve --port 8766`.
2. In Chrome/Edge `http://127.0.0.1:8766/benchmarks/audio_core/index.html` öffnen, Audio-Gerät wählen,
   Lautstärke niedrig einstellen, „Messung starten“. 30 Minuten im Vordergrund ohne Gerätewechsel laufen lassen.
   Abbruch, Tabwechsel, suspendierter Context und verlorene Blöcke werden ausgewiesen.
3. Rohmessung speichern (keine Audioaufnahme). `python -m benchmarks.audio_core.format_result wp04-rohmessung.json --out benchmarks/results/wp04-browser.json`.
4. `python -m benchmarks.result benchmarks/results/wp04-browser.json` validiert das WP00-Format.
   Erfolg des Browser-Soaks: completed=true, elapsed_seconds >= 1800, underruns=0,
   skipped_blocks=0, interruptions=0. Underruns zählen fehlende erwartete Wet-Frames.
   Ein fehlender Wet-Frame während bewusstem Dry/Bypass ist kein unerwarteter Underrun.

Geräte-Latenz getrennt messen, nicht aus baseLatency/outputLatency ableiten. Mit sicherem niedrigem Pegel
einen elektrischen Line-Out→Line-In-Loopback oder externes Zweikanal-Messgerät anschließen (kein Mikrofon-Monitoring/Feedback).
Impulsfolge mit mindestens 20 Ereignissen, jeweils bekannte Ausgabeposition und aufgezeichnete Rücklaufposition
auf derselben Geräte-Zeitbasis bestimmen; Differenz in Samples × 1000 / Abtastrate. Messaufbau, Geräte/Treiber,
Rate, Puffer und die Einzelwerte dokumentieren. Als Roundtrip kennzeichnen; nicht als reine Ausgangslatenz
ausgeben. Bei einer externen Referenzmessung der reinen Ausgangslatenz die Werte separat erläutern.
Die gemessenen Roundtrip-Einzelwerte optional als wiederholtes `--latency-ms 12.3` (Beispielsyntax, kein Messwert)
an format_result übergeben. Ohne Messgerät bleiben die Perzentile null.

Nur Browser-Pfad (Transferables, Ring, Worklet, Mixer), synthetischer Gain-Mock; vollständiger E2E-Pfad
mit Sidecar/Supervisor und G2 folgt in WP06. Kein künstlich grünes Gate. Keine Messung auf Zielhardware erfolgt.
