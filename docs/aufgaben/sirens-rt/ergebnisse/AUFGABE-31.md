# AUFGABE-31 – DSP-Steuerlatenz (WP31)

Depends-on: WP09, WP17/26, G4-Folge WP19.

## Umsetzung
- Fast: Wet-Rampen im Rack 256 → 128 Frames, Morph 512 → 448 Frames (bestehende Klickgrenze bei gegenphasigen IRs). Bypass, andere Profile sowie spektrale und granulare Parameter-Rampen unverändert; Klangqualität nicht ohne Hörtest gefährden.
- Festes Rack-Delay 896 Frames (512 STFT + 256 Granular + 128 Faltung) unverändert, damit Spuren und Core-Uhr synchron bleiben. Produkt-Worklet und Loop/Epoch nicht geändert.
- Browser-Probe misst Empfang, 1 % und 90 % der Wet-Zielwirkung mit zwei synchronen stationären Referenzpfaden. Pro Befehl Ausgabezeitstempel, baseLatency, outputLatency und Render-Phasen.
- Report: Gesamtlatenz und Sirens-Latenz (je gepaarter Stichprobe abzüglich baseLatency und outputLatency), Nachrichtenweg als Restschätzung, Render-Phasen und Rack-Signallaufzeit separat. Letztere nicht nochmals addieren. Fehlende/inkonsistente Schätzungen ausgeschlossen; Altdaten nur Gesamtwert, keine G3-Kennzahl.

## Abnahme
1. Impuls, definierte IRs (Identität/Stille), stationärer Pegel bei 48 kHz, alte Rampen im selben Rack rekonstruiert. Test: `tests/realtime/dsp_control_latency.test.mjs`. Beobachtete Werte aus den GitHub-Modulen im verfügbaren V8-Kontext (Test-/Assert-Adaption, kein Node-Runner):

| Größe | Vorher | Nachher |
|---|---:|---:|
| Rack-Impuls | 896 Frames / 18,67 ms | 896 Frames / 18,67 ms |
| Wet bis 90 % | 231 Frames / 4,8125 ms | 116 Frames / 2,4167 ms |
| Wet maximale Sample-Flanke (FS) | 0,00097656 | 0,00195313 |
| Morph bis 90 % | 461 Frames / 9,6042 ms | 404 Frames / 8,4167 ms |
| Morph maximale Sample-Flanke (FS) | 0,00048828 | 0,00055805 |

Beide < 30 ms und < 0,01 FS (festgelegte Klickgrenze). Kein Ersatz für Hörtest; keine Geräte-/Nachrichtenlatenz im Offline-Test.

2. `tests/realtime/test_dsp_control_latency.py`: gepaarte synthetische Daten, G3-Feld, getrennte Gesamtlatenz, fehlende/inkonsistente Werte, Altdaten und ungültige Werte. Erwartung p95 Gesamt 100 ms, Sirens 20 ms, Nachricht 16 ms. Python-Test nicht ausgeführt.

3. V8-Teilprüfung: 17/17 Fälle aus neuem Test und `dsp_rack.test.mjs`, `dsp_granular_convolution.test.mjs`, `dsp_spectral.test.mjs` bestanden, inkl. bestehender Morph-Klickgrenze < 0,001 FS. Gesamtsuite unter Node 22/Python 3.11/Windows nicht ausgeführt: lokaler Checkout scheiterte mit `fatal: unable to access ... Could not resolve host: github.com`. GitHub-Connector funktioniert. Actions ausgeschaltet; maßgebliche Prüfung durch Koordinator.

4. Browser-Messung am Zielgerät Windows/RTX 5080 **nicht gemessen**. Historisch G4 p50 79,7 ms, p95 82,7 ms, p99 83,3 ms (erste messbare Änderung, geschätzte Ausgabezeit; nicht direkt vergleichbar mit neuer 90-%-Kennzahl). Gerät, Nachricht und Render-Zeiten vorher nicht getrennt verfügbar.

## Nachstellen
Im Repo-Wurzelverzeichnis (Windows):
```powershell
node --test tests/realtime/dsp_control_latency.test.mjs
py -3.11 -m unittest discover -s tests/realtime -p test_dsp_control_latency.py -v
py -3.11 -m unittest discover -s tests -v
py -3.11 -m http.server 8765 --bind 127.0.0.1
```
Chromium/Edge: http://127.0.0.1:8765/benchmarks/dsp/ öffnen, fast, 1 Stem, Messen, JSON nach `benchmarks/results/local/dsp-browser.json` speichern (Ordner anlegen, nicht committen).
```powershell
py -3.11 -m benchmarks.dsp.report benchmarks/results/local/dsp-browser.json benchmarks/results/local/dsp-browser-result.json
py -3.11 -m benchmarks.result benchmarks/results/local/dsp-browser-result.json
```
G3: vollständige plausible Stichproben, p95 Sirens ≤ 50 ms, keine Dropouts, Hörtest. Gesamtlatenz zusätzlich prüfen. Profile/Spurzahl nach WP09 wiederholen.

## Grenzen, Risiken, Rückbau
- Browser-/Treiber-Zeitstempel und Gerätelatenz sind Schätzungen; kein physischer Loopback. Stichprobenzahlen beachten. Eine weitere Referenzspur erhöht CPU-Last.
- Kürzere Wet-Rampe für kontrolliertes Signal belegt; extreme Effektsprünge und weitere Regler im Hörtest prüfen. Gate-Status nicht geändert. Kein Eingriff außerhalb der Kette.
- Python 3.11, Node 22 (vorgesehene Prüfung), ES-Module/Web Audio API; keine neuen Fremdprojekte, Pins, Lizenzen, Gewichte oder Downloads. CPU für Offline-Test; Zielgerät für Browser/Hörtest.
- Rückbau: AUFGABE-31-Commits revertieren; keine Migration. Lokale Benchmark-Ausgaben entfernen; Browser/HTTP-Server schließen.
