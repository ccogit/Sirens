# AUFGABE-00 – Baseline und Testgerüst (WP00)

**Status: lokal vorbereitet, teilweise geprüft; nicht zur Integration freigegeben.**
Keine Voraussetzungen. Basis: `integration/sirens-rt` bei `a9d5fbf5c39e9399ddf52647d033dfc3c1f74286`.
Branch: `extern/KETTE-00`. Die GitHub-Schnittstelle hat Schreibzugriff und der Branch wurde von diesem SHA angelegt. Der Code-Push und Draft-PR sind wegen des fehlenden vollständigen Regressionstests bewusst nicht erfolgt.

## Umsetzung

- Rekursive, sortierte Node-Test- und JS-Syntax-Suche in `tests/test_web.py`; ursprüngliche Tests bleiben erhalten. Verschachtelter positiver Node-Test sowie Negativtests für beide Finder.
- Standardbibliothek-Module für synthetische PCM24-Fixtures, Track-Manifest, Ergebnisformat und datensparsame Baseline; JSON-Schema, Beispieldaten, ADR-, Board- und Dokumentationsvorlagen. Lokales Manifest und lokale Ergebnisse ignoriert.
- Kein Code in `sirens/` oder `web/` geändert; kein CI-Umbau und keine Änderung des Kettenregisters. Keine zusätzlichen Zweige, Modellgewichte, Musikdateien oder Dependencies.

## Abnahmebelege

| Nr. | Nachweis | Stand |
|---|---|---|
| 1 | `python -m unittest discover -s tests -v` im vollständigen Checkout, Python 3.11 / Node 22. Lokaler Teilbaum enthielt lediglich die zwei aus dem Zielbranch gelesenen Originaldateien und die neuen Dateien. Der Versuch der Discovery fand 18 Tests, davon 17 ohne Fehler, ein Fehler wegen fehlender `web/js/logic.js`; vorhandene Regressionstests fehlen im Teilbaum. | Offen; weder vorherige Testzahl noch Gesamttest/CI belegt |
| 2 | `test_web.Seite.test_logik_mit_node` lief im Teilbaum grün mit `tests/realtime/beispiel.test.mjs`. `test_node_fehler_aus_unterordner` belegt zusätzlich die Ausführung und Fehlerausgabe, `test_syntax_fehler_aus_unterordner` die rekursive Syntaxprüfung. | Teilprüfung bestanden |
| 3 | `realtime.test_fixtures`: fünf Tests, darunter bytegleiche WAVs aller acht Signale, 120/140/150 BPM, 24.000 Frames bei 120 BPM/48 kHz, Taktakzente, Impuls, Stille, WAV-Header, Samplegrenzen und Stereo-Frequenzen. | Teilprüfung bestanden |
| 4 | `realtime.test_benchmark_tools.Result`: gültiges Beispiel und Bericht, fehlende Pflichtfelder, unbekanntes Gate, ungültige Werte und Perzentile. | Teilprüfung bestanden |
| 5 | `realtime.test_benchmark_tools.Manifest`: fehlende Datei, falscher Hash, Hash-Ergänzung und erneute Prüfung; nur temporäre synthetische Bytes. | Teilprüfung bestanden |
| 6 | `realtime.test_benchmark_tools.Baseline`: gemockte Werkzeugaufrufe, fehlende NVIDIA-/ffmpeg-Daten = null, keine Benutzerpfade; GPU-CSV nur synthetischer Testwert. | Teilprüfung bestanden; Zielrechner nicht gemessen |
| 7 | Neue Tests ausschließlich temporäre Daten, CPU, Python-Standardbibliothek und Node-Builtins; keine Downloads. Die bestehende vollständige Suite wurde hier nicht ausgeführt. | Neue Tests bestanden; Gesamtsuite offen |

Konkreter lokaler Teilprüfungsbefehl (im vollständigen Checkout ebenfalls möglich; POSIX-Syntax):

```sh
PYTHONPATH=tests python -m unittest realtime.test_fixtures realtime.test_benchmark_tools realtime.test_web_discovery test_web.Seite.test_logik_mit_node -v
node --test tests/realtime/beispiel.test.mjs
```

Ausgabe: `Ran 15 tests` / `OK`; Node: `1 pass, 0 fail`. CLI-Smoke-Test in temporärem Ordner: acht WAVs und acht Wahrheits-JSONs, Baseline-JSON erfolgreich erzeugt. Lokale Laufzeit Python 3.13.5, Node 22.16.0; Python 3.11 war nicht vorhanden. Der lokale Test belegt keine Zielhardwareleistung.

## Nicht gemessen / Abweichungen / Risiken

- Zielrechner Windows 11/RTX 5080: nicht gemessen. Aufruf: `python -m benchmarks.baseline --out benchmarks/results/local/baseline.json`, Fixture-Aufruf siehe `docs/realtime/baseline.md`. Audio-Gerät und Treiber sind als manueller Schritt dokumentiert und im JSON `audio_device: null`, da keine datensparsame plattformübergreifende Abfrage implementiert wurde. WSL ist bei erfolgreicher Abfrage `true`, andernfalls `null` mit Hinweis. Tatsächliche Windows-Toolausgaben sind nicht geprüft.
- Determinismus gilt für wiederholte Aufrufe in derselben Laufzeitumgebung; plattformübergreifende Sinus-Bitidentität ist nicht geprüft.
- Vollständiger Git-Checkout scheiterte an fehlender DNS-Auflösung für `github.com`. Die Original-Blobs für `.gitignore` und `tests/test_web.py` wurden über die GitHub-Schnittstelle gelesen und per `git hash-object` gegen den Basisbaum verifiziert. Die vorgeschriebene grüne Gesamtsuite vor Push verhindert einen Remote-Code-Push. Deshalb auch keine PR-CI, kein Ready-for-review und keine Aussage über vollständige Abnahme. Die Board-Vorlage hat WP00 gemäß Aufgabenforderung `review`, dokumentiert aber ausdrücklich den offenen Gesamttest.
- Keine fremden Projekte, Modellgewichte, Pins oder zusätzlichen Lizenzen. Laufzeit: Python 3.11 (Standardbibliothek) und Node 22; kein GPU-Bedarf für Tests. Die Lizenz lokaler Tracks muss der Koordinator prüfen; Manifest validiert nur Metadaten und Datei-Hash.

## Nachstellen, offene Schritte, Rückbau

Im vollständigen Checkout des Branches Patch anwenden, vor Push die vollständige Suite mit Python 3.11/Node 22 grün prüfen und mit dem unmodifizierten Basisstand vergleichen. Danach Commit mit `AUFGABE-00: Baseline und Testgerüst`, Push ohne Force, genau einen Draft-PR gegen `integration/sirens-rt`; CI prüfen und Bericht aktualisieren. Vor Übergabe den Integrationsstand prüfen/mergen. Zielhardware-Baseline durch Koordinator.

Rückbau: Patch rückwärts anwenden bzw. nach Commit diesen revertieren; neue Module, Tests und Dokumentation sind isoliert. Keine produktiven Daten oder Originalmusik werden verändert. Der Branch enthält zum Zeitpunkt der lokalen Vorbereitung noch keine abweichenden Commits.
