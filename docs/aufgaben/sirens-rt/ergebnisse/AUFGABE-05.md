# AUFGABE-05 – Live Lab Shell und GPU-Anzeige (WP05)

PR [#12](https://github.com/ccogit/Sirens/pull/12), extern/KETTE-23 → integration/sirens-rt. Depends-on: WP01/KETTE-11. Branch vom Integrationsstand 9e1ae563; vorgezogen per Fast-forward auf 05592a62, erster eigener Commit 110be09d und sofort Draft-PR. Erneute Übernahme der Vertragsbasis 7f69f454 und der Integration in e2783e71; nach Merge von KETTE-11 aktualisiert auf Integrationsstand ae58b386 (Merge cafdd8f8). Kein Force-Push. Register und Board nur unverändert aus ihren jeweiligen Ursprungscommits übernommen, nicht eigenständig bearbeitet.

## Umsetzung

- RTX Neural Lab als zusätzliches Spielzeug mit isoliertem CSS, minimaler Registrierung in live_lab.js und index.html. main.js bleibt unverändert. Mount/Pause/Destroy entfernen alle registrierten Listener und den Poll-Timer; keine AudioContext-Erzeugung.
- RT-Control-API, strikt expliziter lokaler Mock bei serverseitig gemeldeter Mock-Fähigkeit, Fehlerzustände, Capability-/Moduslabels und Installationshilfe. GPU-Panel zeigt VRAM, Queue, Compute, Temperatur, Deadline-Fehler, Underruns und deklarierte Latenz (nicht gemessen).
- Song-Katalog und vorhandener Demucs-Stem-Cache ausschließlich lesend; synthetisches Mock-Asset separat auswählbar. Kein Start von Trennung oder Modell. Play/Pause/Seek/Stop, Gain, Dry/Wet, Bypass, Panic, A/B, lokale Presets und Tastatur; MIDI-Datenstruktur ohne Gerätezugriff.
- Keine Änderungen an sirens/ durch WP05; keine neuen Frameworks oder Abhängigkeiten.

## Abnahme

| Punkt | Beleg | Stand |
|---|---|---|
| 1 | tests/realtime/lab_shell.test.mjs: Schalter aus, keine GPU, kein Modell, Mock, API-Fehler, leere Bibliothek, busy_gpu; Presets, Key- und MIDI-Mapping; kombinierter GPU-503/fehlendes Modell | Code-CI 45452920608 grün; Ergänzungen in Schluss-CI |
| 2 | Node-Tests: Mount/Pause/Destroy mit Listener-/Timer-/AudioContext-Zählern, späte Antwort, wiederholter Mount, Session-Reset, Destroy während Create | Code-CI grün; zusätzlicher Race-Test in Schluss-CI |
| 3 | Node-Tests: HTTP 503, 409, ungültiges JSON und falsche Antwortstruktur; deaktivierte Bedienung | Code-CI grün; Sichtprüfung nicht gemessen |
| 4 | Registrierung nur ein zusätzliches Spielzeug, keine Änderung bestehender Routen; test_javascript_module_syntax und test_logik_mit_node in Code-CI bestanden | Bestandssuite grün; Browser-Sichtprüfung nicht gemessen |
| 5 | docs/realtime/hooks/WP05.md, benchmarks/lab_shell/check.py, tests/realtime/test_lab_shell_benchmark.py; Ergebnisformat aus benchmarks/result.py | nicht gemessen; Koordinator führt manuelle Schritte aus |
| 6 | python -m unittest discover -s tests -v | [Code-CI 45452920608](https://github.com/ccogit/Sirens/actions/runs/45452920608): 101 Tests, OK (skipped=4); Schluss-CI siehe PR-Checks. Board entfällt gemäß KETTEN.md. |

Erster Draft-Lauf 45452508285 fehlgeschlagen, da Zustands-Test vor Implementierung gepusht wurde; nach Umsetzung Code-CI grün. Lokaler vollständiger Checkout nicht möglich: git ls-remote https://github.com/ccogit/Sirens.git … meldete "fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com" (128). CI ist maßgeblich.

## Nachstellen

- python -m unittest discover -s tests -v
- node --test tests/realtime/lab_shell.test.mjs
- python benchmarks/lab_shell/check.py --out benchmarks/results/wp05-lab-shell.json
- python benchmarks/result.py benchmarks/results/wp05-lab-shell.json

Hardware: CPU für Tests ausreichend; Browser-Sichtprüfung am Zielrechner Windows/RTX 5080 **nicht gemessen**. Kein Audio-/Leistungsgate in WP05. Python 3.11, Node 22, Standardbibliothek bzw. ES-Module. Keine fremden Projekte, Gewichte, zusätzlichen Lizenzen oder Commit-Pins; bestehende WP01-Verträge verwendet.

## Anpassungsbedarf / Grenzen / Risiken

- WP01 stellt nur GET capabilities bereit. Der lokale Mock kann nur eine synthetische Asset-ID laden; ausgewählte Katalog-Songs/Stems werden nicht als RT-Assets geladen und keinesfalls abgespielt. Beschriftung erklärt dies ausdrücklich. Reale Session-/Asset-Auflösung und Dry/Wet am einzigen Audio-Core kommen in WP06 (Hook). Gain und Bypass werden an Mock-Befehle übergeben, Dry/Wet ist bis dahin UI-Zustand; Panic schließt die Mock-Sitzung, setzt Dry und stumm. Keine echte Audioausgabe oder physische Stummschaltung in WP05.
- GPU-Mock meldet keine GPU; reale Telemetrie bei deaktiviertem Mock erst mit WP03. 503 bei capabilities lässt RT ausgeschaltet oder nicht verfügbar nicht unterscheiden; beides wird benannt. 503 bei GPU wird als API-Fehler angezeigt, fehlende Freigabe bleibt sichtbar. Moduslabels sind deklarierte Fähigkeiten, keine Leistungsbehauptung.
- Presets sind lokale A/B-Mischparameter ohne Katalogpfade/Kundendaten. MIDI nur Mapping. Kein frei wählbarer Worker, kein Download.
- Browserlayout, echte Gerätebedienung und Interaktion mit den bereits vorhandenen Visual-/Audioressourcen des Bestands wurden nicht am Zielrechner geprüft. WP05 selbst hat keine Audio-/GPU-Engine.
- Die explizit geforderte Sichtprüfungsdatei liegt unter benchmarks/lab_shell/; die Anleitung als erlaubter WP05-Hook. Keine Änderung an WP01-Vertragsdateien.
- Rückbau: PR nicht mergen oder ausschließlich WP05-Änderungen revertieren (nicht Vertrags-/Integrationsmerges). Entfernen der Registrierung/CSS deaktiviert den Bereich; Schalter aus sperrt RT. Lokale Presets unter sirens.rt.presets.v1 können gelöscht werden.

## Übergabe

Fertig: Shell, Mock-Steuerung, Registrierung, Tests und Sichtprüfungsanleitung gepusht. Offen: Schluss-CI am endgültigen Head prüfen und Zielrechner-Sichtprüfung durchführen; bei roter CI zuerst deren Joblog auswerten. Code-CI war bereits grün; keine lokalen Tests wegen obigem DNS-Fehler. WP06 übernimmt reale Audio-/Asset-Anbindung, nicht Teil dieser Aufgabe.
