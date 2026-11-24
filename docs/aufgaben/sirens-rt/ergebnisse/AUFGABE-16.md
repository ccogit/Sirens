# AUFGABE-16 – Recorder, Session, Export

WP16; Depends-on WP01, WP04; Einbau und Live-Session-Replay durch WP06 (Hook).
Implementiert: Master-Abgriff per separatem stummem AudioWorklet, acht Transferpuffer,
sequenzieller Upload mit Frame-Bestätigung und Abbruchmeldung; PCM24-Stereo-WAV
mit RIFF-Segmentierung, Größenlimit, Speicherplatzreserve, temporären Dateien
und Reparatur; kollisionsfreie Aufnahme- und Session-Verzeichnisse; eigenes
Session-Dateischema, Quellen-Hashes, Versionen, Seeds, Asset-IDs und Timeline,
CPU-Parameter-Replay. Kein MediaRecorder, keine Fremdbibliotheken.

## Abnahmepunkte

1. `test_fixture_segments`: Float32-Fixture gegen PCM24 innerhalb einer Stufe,
   Abtastrate, Kanäle, Dauer, Segmentwechsel, 32-bit-RIFF-Grenze im Kopf.
2. `test_repair_and_collision`, `test_disk_full`, `test_limit_and_path`:
   abgebrochener Frame wird entfernt, Namen kollisionsfrei, simulierte volle
   Platte schließt gültiges Segment, Gesamtlimit erzwungen.
3. `test_session`: Session-Roundtrip, Parameter-Replay, negativer Seed abgelehnt.
4. `test_limit_and_path` und `test_session`: Musikordner und Traversal abgelehnt.
5. **Nicht gemessen**: Zielrechner/Browser. 30 Minuten, 48 kHz Stereo PCM24
   entsprechen 86.400.000 Frames und 518.400.000 Nutzdatenbytes.
   Aufruf aus Repo-Wurzel, Scratch-Verzeichnis außerhalb Musikordner/Repo wählen:
   ```
   python -m benchmarks.recorder.measure --scratch <scratch> --out benchmarks/results/wp16-disk.json
   python -m benchmarks.recorder.browser --scratch <scratch> --out benchmarks/results/wp16-browser.json
   python -m benchmarks.result benchmarks/results/wp16-browser.json
   ```
   Beim zweiten Aufruf ausgegebene Loopback-Adresse in Chromium öffnen,
   Ausgabegerät auf 48 kHz stellen, Lautstärke niedrig, Start klicken,
   Tab sichtbar lassen, Ergebnis abwarten, dann Strg+C. Kurzlauf mit
   --seconds 2 möglich. Browser-Messung nutzt Test-HTTP-Adapter, nicht
   Produktions-Session-API; Geräte-Latenz nicht erfasst. Kein Gate freigegeben.
6. `python -m unittest discover -s tests -v`, CI PR #14 maßgeblich.
   Lauf 45452744626: 106 Tests, Fremdimport-Prüfung aus WP01 rot (basic_pitch).
   Integration aktualisiert, WP01-Validator nach schemas/__init__.py verschoben;
   Import angepasst. Lauf 45453172540: 111 Tests, 4 übersprungen, fünf
   Recorder-Python-Tests grün; Node-Test scheiterte an Groß-/Kleinschreibung
   der Fehlermeldung (Aufnahmebestätigung statt Bestätigung), korrigiert.
   Lauf 45453374006 (ac2fb2a): **grün**, 115 Tests, OK (skipped=4),
   einschließlich aller Recorder-Python-Tests und des rekursiven Node-Laufs.
   Anschließend Integration 329db19 und Audio-Kern 8b58186 erneut gemergt;
   Lauf 45453507588 (2337180): **grün**, 116 Tests, OK (skipped=4),
   alle Recorder-Tests und Node-Lauf erfolgreich. Nachfolgend ausschließlich
   Dokumentation des Prüfbelegs. Kein lokaler Checkout:
   git ls-remote scheiterte mit "Could not resolve host: github.com".
   Board und Register nicht eigenständig bearbeitet.

## Anpassungsbedarf / Risiken

- WP06: Adressen, Authentisierung, Export-Asset-Registrierung, Lease und
  Session-Replay im Dienst gemäß docs/realtime/hooks/WP16.md. Upload separat
  vom eingefrorenen Sidecar-Protokoll, um Restblöcke zu erlauben.
- CPU-Replay stellt numerische Parameter wieder her; Quell-Hash-Verifikation,
  Transport/Modelle, Bypass-Zustand und echte zeitgesteuerte Wiedergabe gehören
  in die noch fehlende Session-Integration. Generative Modelle nicht
  notwendigerweise bitidentisch. Vollständige Session-Wiedergabe nicht geprüft.
- 24-bit Quantisierung, Standardlimit 16 GiB, Reserve 1 MiB. Pro Segment
  maximal RIFF-kompatible Nutzdaten; bei schwerem I/O-Ausfall bleibt .part
  zur Reparatur, kein Versprechen bei physischem Datenträgerdefekt.
- Browser/HTTP-Testadapter und Hardwaremessung noch nicht ausgeführt.
- Python 3.11, Node 22 (CI), Web Audio API; keine fremden Projekte, Gewichte,
  Pins oder zusätzliche Lizenzen. Keine GPU für CPU-Tests erforderlich.

## Rückbau

Eigene WP16-Dateien entfernen bzw. eigene Commits revertieren; keine
Abhängigkeits-Merge-Commits zurückrollen. Keine Aktivierung ohne Hook.
Exportdaten im separaten Aufnahmeordner bleiben erhalten.

## Einbau durch WP06 und Koordinator

Eigenständige Module, CPU-/Node-Tests, Hook und zwei Messskripte gepusht.
Nächste Schritte außerhalb dieser Kette: Hook durch WP06 einbauen und Soak
am Zielrechner ausführen. Fehlerausgaben und korrigierte CI-Läufe siehe oben.
