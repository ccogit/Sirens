# WP09 – Messung (CPU/GPU-Vergleich vorbereitet)

Keine Downloads, nur synthetische Signale. Zielhardware nicht gemessen. Für Node 22 im Repo-Wurzelverzeichnis:

```sh
node benchmarks/dsp/measure.mjs fast 1 > benchmarks/results/local/dsp-node.json
python -m benchmarks.dsp.report benchmarks/results/local/dsp-node.json benchmarks/results/local/dsp-node-result.json
python -m benchmarks.result benchmarks/results/local/dsp-node-result.json
```

Zielordner vorher anlegen. Je Profil fast/standard/detail und 1/2/4/8 Stems wiederholen; gleiche 48-kHz-375-Hz-Sinusquelle, 128 Frames pro Stichprobe, 1000 kalte/warme Blöcke. RTF und Blockzeit messen, nicht mit Geräte-Latenz verwechseln. Vergleichsbackend muss dieselben Inputs, Profile, Blockgrößen und Effektparameter verwenden; kein GPU-Backend vorhanden.

Browser: `python -m http.server 8765 --bind 127.0.0.1` im Repo-Wurzelverzeichnis; in Chromium/Edge http://127.0.0.1:8765/benchmarks/dsp/ öffnen, gewünschtes Profil und Stems wählen, Messen klicken. Erst neutraler Impuls, dann drei Rack-Familien pro Spur (Cloud-Preset); zwei zusätzliche Referenzpfade messen Steuerantwort. Ausgabezeitstempel des AudioContext und erster messbar geänderter Sample liefern Control-to-audio-Schätzung; Render-Ack separat. 100 Stichproben pro Kombination, bei Timeout abbrechen. JSON speichern (nicht ins Repo committen) und mit `python -m benchmarks.dsp.report <browser.json> <result.json>` validieren. Physische Geräte-Latenz und Dropouts separat mit Loopback-Aufnahme/Audio-Treiberzählern prüfen; keine Freigabe aus geschätzter Ausgabezeit ableiten. Standard für Live-Versuch fast (896 Frames, bei 48 kHz rund 18,67 ms, deklarierter Wert). Standard/detail als höherlatente Profile kennzeichnen. G3: Zusatzlatenz Ziel <=20 ms, p95 Control-to-audio <=50 ms; kein Dropout im freigegebenen Profil. Hörtest aller drei Familien einschließlich Freeze/Mask/Pitch und Stretch mit generiertem Clip; Werte erst am Zielrechner protokollieren.

Rückbau: Browser schließen und lokalen HTTP-Server beenden.
