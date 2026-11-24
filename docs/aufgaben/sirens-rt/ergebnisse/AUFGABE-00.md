# AUFGABE-00 – Baseline und Testgerüst (WP00)

**Status: umgesetzt; Code-CI grün, zur Prüfung durch A0 vorgesehen.**
Keine Voraussetzungen. Ausgangsbasis: `integration/sirens-rt` bei `a9d5fbf5c39e9399ddf52647d033dfc3c1f74286`.
Branch: `extern/KETTE-00`; [PR #7](https://github.com/ccogit/Sirens/pull/7) gegen `integration/sirens-rt`.
Aufgabencommit `b2be62ec2107f7a4c6e487d3b29e2c257ed6611f`. Der aktualisierte Integrationsstand `3bff0c5fcc1efd7990db0dd72a97418279bdd162` wurde konfliktfrei per Merge-Commit `8833bf7d43979bf80be3f56c6a33e3d18490fa04` übernommen (kein Force-Push). Die geänderten Register- und Regeldateien stammen ausschließlich vom Koordinator. Maßgeblich ist gemäß aktueller Regel die PR-CI.

## Umsetzung

- Rekursive, sortierte Node-Test- und JS-Syntax-Suche in `tests/test_web.py`; ursprüngliche Tests bleiben erhalten. Verschachtelter positiver Node-Test sowie Negativtests für beide Finder.
- Standardbibliothek-Module für synthetische PCM24-Fixtures, Track-Manifest, Ergebnisformat und datensparsame Baseline; JSON-Schema, Beispieldaten, ADR-, Board- und Dokumentationsvorlagen. Lokales Manifest und lokale Ergebnisse ignoriert.
- Kein Code in `sirens/` oder `web/` geändert; kein CI-Umbau und keine eigene Änderung des Kettenregisters. Keine zusätzlichen Zweige, Modellgewichte, Musikdateien oder Dependencies.

## Abnahmebelege

Maßgeblicher Code-CI-Lauf: [Tests #45450322540](https://github.com/ccogit/Sirens/actions/runs/45450322540), [Job tests](https://github.com/ccogit/Sirens/actions/runs/45450322540/job/138645364943), Head `8833bf7d43979bf80be3f56c6a33e3d18490fa04`, Ubuntu, Python 3.11.18, Node v22.23.5. Workflow und Job abgeschlossen mit `success`. Der erste Lauf wurde durch die Aktualisierung des Branches von der bestehenden CI-Concurrency abgebrochen, nicht wegen eines Testfehlers.

```
python -m unittest discover -s tests -v
Ran 91 tests in 13.547s
OK (skipped=4)
```

| Nr. | Nachweis | Stand |
|---|---|---|
| 1 | CI-Log: 77 bestehende Testfälle (davon 4 bestehende umgebungsbedingte Skips) und 14 neue Python-Testfälle unter `realtime.`, alle 14 erfolgreich. Bestehende Testdateien unverändert außer den zwei gezielten Finder-Änderungen; kein vorhandener Test entfernt. | Grün |
| 2 | `test_web.Seite.test_logik_mit_node` und `test_javascript_module_syntax` in CI erfolgreich. `tests/realtime/beispiel.test.mjs` wird per rekursivem Glob ohne Liste ausgeführt; die beiden Discovery-Negativtests belegen Fehlererkennung und Ausgabe auch im Unterordner. | Grün |
| 3 | `realtime.test_fixtures`: fünf Tests, darunter bytegleiche WAVs aller acht Signale, 120/140/150 BPM, 24.000 Frames bei 120 BPM/48 kHz, Taktakzente, Impuls, Stille, WAV-Header, Samplegrenzen und Stereo-Frequenzen. | Grün |
| 4 | `realtime.test_benchmark_tools.Result`: gültiges Beispiel und Bericht, fehlende Pflichtfelder, unbekanntes Gate, ungültige Werte und Perzentile. | Grün |
| 5 | `realtime.test_benchmark_tools.Manifest`: fehlende Datei, falscher Hash, Hash-Ergänzung und erneute Prüfung; nur temporäre synthetische Bytes. | Grün |
| 6 | `realtime.test_benchmark_tools.Baseline`: gemockte Werkzeugaufrufe, fehlende NVIDIA-/ffmpeg-Daten = null, keine Benutzerpfade; GPU-CSV nur synthetischer Testwert. | Grün; Zielrechner nicht gemessen |
| 7 | Neue Tests ausschließlich temporäre Daten, CPU, Python-Standardbibliothek und Node-Builtins; keine Downloads. Der unveränderte CI-Testbefehl läuft ohne GPU, Modelle oder echte Musik. | Grün |

Vier bestehende Skips: drei Kicktausch-Tests (numpy/scipy/soundfile nicht installiert), ein Mastering-Test (ffmpeg fehlt). Keine neuen Skips. Der unmodifizierte Basisstand wurde nicht separat ausgeführt; Bestandserhalt ist durch unveränderte Testmethoden und die 77 im CI-Log identifizierten bestehenden Tests belegt.

Lokale Teilprüfung (zusätzlich, nicht maßgeblich; POSIX-Syntax):

```sh
PYTHONPATH=tests python -m unittest realtime.test_fixtures realtime.test_benchmark_tools realtime.test_web_discovery test_web.Seite.test_logik_mit_node -v
node --test tests/realtime/beispiel.test.mjs
```

Ausgabe: `Ran 15 tests` / `OK`; Node: `1 pass, 0 fail`. CLI-Smoke-Test in temporärem Ordner: acht WAVs und acht Wahrheits-JSONs, Baseline-JSON erfolgreich erzeugt. Lokale Laufzeit Python 3.13.5, Node 22.16.0; vollständiger lokaler Git-Checkout scheiterte an DNS-Auflösung. Die CI hat die Gesamtsuite unter den vorgesehenen Versionen nachgeholt.

## Nicht gemessen / Abweichungen / Risiken

- Zielrechner Windows 11/RTX 5080: **nicht gemessen**. Aufruf: `python -m benchmarks.baseline --out benchmarks/results/local/baseline.json`, Fixture-Aufruf siehe `docs/realtime/baseline.md`. Audio-Gerät und Treiber sind als manueller Schritt dokumentiert und im JSON `audio_device: null`, da keine datensparsame plattformübergreifende Abfrage implementiert wurde. WSL ist bei erfolgreicher Abfrage `true`, andernfalls `null` mit Hinweis. Tatsächliche Windows-Toolausgaben sind nicht geprüft.
- Determinismus gilt für wiederholte Aufrufe in derselben Laufzeitumgebung; plattformübergreifende Sinus-Bitidentität ist nicht geprüft.
- Vier bestehende optionale Tests wurden in der CI übersprungen (siehe oben); die Zielhardware und optionale Werkzeuge bleiben vom Koordinator zu prüfen. Die CI meldet außerdem eine bestehende Deprecation-Warnung zu den verwendeten GitHub-Actions-Versionen. Kein Workflow-Umbau im Umfang von WP00.
- Keine fremden Projekte, Modellgewichte, Pins oder zusätzlichen Lizenzen. Laufzeit: Python 3.11 (Standardbibliothek) und Node 22; kein GPU-Bedarf für Tests. Die Lizenz lokaler Tracks muss der Koordinator prüfen; Manifest validiert nur Metadaten und Datei-Hash.

## Nachstellen und Rückbau

`python -m unittest discover -s tests -v` in vollständigem Checkout mit Python 3.11/Node 22 ausführen. Weitere Befehle: `benchmarks/README.md` und `docs/realtime/baseline.md`. Zielhardware-Baseline durch Koordinator. Der abschließende Dokumentationscommit wird erneut durch dieselbe PR-CI geprüft; der aktuelle Check-Status steht im PR.

Rückbau: Aufgabencommit und abschließenden Dokumentationscommit revertieren; die übernommenen Koordinator-Änderungen im Integrationszweig nicht rückgängig machen. Neue Module, Tests und Dokumentation sind isoliert. Keine produktiven Daten oder Originalmusik werden verändert.
