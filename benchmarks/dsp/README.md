# WP09 – Messung (CPU/GPU-Vergleich vorbereitet)

Keine Downloads, nur synthetische Signale. Zielhardware nicht gemessen. Für Node 22 im Repo-Wurzelverzeichnis:

```sh
node benchmarks/dsp/measure.mjs fast 1 > benchmarks/results/local/dsp-node.json
python -m benchmarks.dsp.report benchmarks/results/local/dsp-node.json benchmarks/results/local/dsp-node-result.json
python -m benchmarks.result benchmarks/results/local/dsp-node-result.json
```

Zielordner vorher anlegen. Je Profil fast/standard/detail und 1/2/4/8 Stems wiederholen; gleiche 48-kHz-375-Hz-Sinusquelle, 128 Frames pro Stichprobe, 1000 kalte/warme Blöcke. RTF und Blockzeit messen, nicht mit Geräte-Latenz verwechseln. Vergleichsbackend muss dieselben Inputs, Profile, Blockgrößen und Effektparameter verwenden; kein GPU-Backend vorhanden.

Browser: `python -m http.server 8765 --bind 127.0.0.1` im Repo-Wurzelverzeichnis; in Chromium/Edge http://127.0.0.1:8765/benchmarks/dsp/ öffnen, gewünschtes Profil und Stems wählen, Messen klicken. Erst neutraler Impuls, dann drei Rack-Familien pro Spur (Cloud-Preset); ein hörbarer Probe-Pfad und zwei stationäre Referenzpfade (Wet=0/1) messen die Steuerantwort. Die Probe erfasst den Empfang, die erste Änderung (>1 % der Referenzdifferenz) und 90 % der Zielwirkung. Ausgabezeitstempel des AudioContext liefern die geschätzte Gesamtlatenz bis 90 %; Render-Ack separat. 100 Stichproben pro Kombination, bei Timeout abbrechen. JSON speichern (nicht ins Repo committen) und mit `python -m benchmarks.dsp.report <browser.json> <result.json>` validieren. Physische Geräte-Latenz und Dropouts separat mit Loopback-Aufnahme/Audio-Treiberzählern prüfen; keine Freigabe aus geschätzter Ausgabezeit ableiten. Standard für Live-Versuch fast (896 Frames, bei 48 kHz rund 18,67 ms, deklarierter Wert). Standard/detail als höherlatente Profile kennzeichnen. G3: Zusatzlatenz Ziel <=20 ms, p95 Sirens-Control-to-audio (ohne Gerätelatenz) <=50 ms; kein Dropout im freigegebenen Profil. Hörtest aller drei Familien einschließlich Freeze/Mask/Pitch und Stretch mit generiertem Clip; Werte erst am Zielrechner protokollieren.

Rückbau: Browser schließen und lokalen HTTP-Server beenden.

## WP31 – Zerlegung der Steuerlatenz

- `control_ms`: geschätzte Ausgabezeit des 90-%-Samples minus Sendezeit.
- `control_samples`: gepaarte Schätzung je Befehl mit baseLatency und outputLatency (ms),
  deklarierter Rack-Signallaufzeit, Empfang bis 1 % und 1 bis 90 % Zielwirkung.
- `latency_breakdown` im Ergebnis: p50/p95/p99 je Größe und Stichprobenzahlen.
  Die G3-Kennzahl in `messwerte.warm` ist die Gesamtlatenz abzüglich baseLatency
  und outputLatency je Stichprobe. Nachrichtenweg = Sirens-Latenz minus beide
  Render-Phasen (Restschätzung). Die feste Rack-Signallaufzeit ist keine zusätzliche
  additive Steuerlatenz: ein Regler am Rack-Ausgang verändert bereits gepufferte
  Audiosamples. Fehlende oder widersprüchliche Schätzungen werden gekennzeichnet;
  für Altdaten ohne gepaarte Gerätelatenzen wird keine Sirens-Kennzahl angegeben.
- Die Messung ist kein physischer Loopback. Browser-/Treiber-Zeitstempel können
  abweichen. Nur vollständige, plausible Stichproben plus Hörtest zur G3-Abnahme
  verwenden; alte Messungen der ersten Änderung nicht direkt mit 90 % vergleichen.

Offline-Abnahme bei 48 kHz (synthetischer Impuls, definierte IRs und stationärer
Pegel; alte und neue Rampen im selben Rack, keine Gerätelatenz):

```sh
node --test tests/realtime/dsp_control_latency.test.mjs
python -m unittest discover -s tests/realtime -p test_dsp_control_latency.py -v
```

Festes Delay des schnellen Profils: 896 Frames wie zuvor; Wet-Rampe 256 → 128
Frames und Morph-Rampe 512 → 448 Frames. Die Morph-Rampe bleibt wegen der Klickgrenze bei gegenphasigen IRs länger. Keine Änderung an Transport oder Epoch.
