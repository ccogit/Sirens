# AUFGABE-27 – Performance Pads Teil 2 (WP12) – ÜBERGABE

Depends-on: WP12 Teilstand (KETTE-35), WP06, WP10, ADR 0006 (KETTE-28), Shell-/Audio-Hook durch Koordinator.
Basis nach Zweieltern-Merge: 62388087f2c2495166f3f19b2301eda68ddb0641 (KETTE-43 Teilstand). Kein Force-Push.
PR #32 gegen integration/sirens-rt. Keine Produktfreigabe.

## Umgesetzt

- Stable-Audio-Worker: Dateijob nach ADR 0006 mit ausschließlich numerischen Manifest-Controls, erneuter
  Validierung, Prompt aus Pad-Typ, Tempo und sicherer Tonart, Seed, Taktlänge und Wet-Anteil. Export
  eines begrenzten Stereo-PCM16-WAV in den privaten Jobordner; die Quelle wird nicht gelesen oder verändert.
  Extend bleibt Prompt-Neugenerierung, kein Inpainting. Keine Änderung des bestehenden Chunk-Pfads.
- `pad_bar.js`: eigenständiger Controller und DOM-Leiste (sechs Typen, Takte, Öffnen/Schließen,
  Vorhören, Einsetzen, Verwerfen, Status). Explizite Nutzeraktion, höchstens ein Kandidat,
  Asset-ID/Format-Prüfung, Epoch-Schutz bei Close, kein automatischer Retry. Backend-Port für
  Load/Warmup, asynchronen Dateijob/Asset und Abbruch/Unload.
- `pad_audio.js`: WebAudio-Bridge mit gemeinsamer AudioContext-Zeitachse, ganzzahliger Startframe-
  Abbildung, komplementären Gain-Rampen, getrenntem Vorhörbus durch den Worklet, Dry bei falscher Epoch,
  Loop, verspäteter Planung oder Überschneidung. Shell muss exakten Play-Anker und Dry-Gain bereitstellen.
- `docs/realtime/hooks/WP12.md`: Einbaupunkte, Supervisor-Code, Controls, Asset-/Lifecycle- und
  Shell-Audio-Vertrag, sichere Sperren und notwendige Anpassung an KETTE-28.
- `benchmarks/pads/report.py`: Auswertung von 20 protokollierten tatsächlichen Einsätzen einschließlich
  Verschiebungen, Dry, Abweichung >1 Sample und Asset-Bereitschaftszeiten. Kein automatisch grünes Gate.

## Abnahme

| Punkt | Beleg | Stand |
|---|---|---|
| 27.1 / 12.1 | `tests/realtime/test_pad_file_job.py` – Fake-Modell, Warmup vor Generate, PCM16-Export, Parametergrenzen, unveränderte Quelle; `tests/realtime/pad_wiring.test.mjs` – Backend-Double, Nutzeraktion, Job bis Asset-Buffer, Shift/Dry, Close, Sampleadresse und Crossfade mit Audio-Double. Vorhandener `pad_scheduler.test.mjs` – Queue, sechs Typen, Preview, Fristen. | Teilweise: isolierte Tests geschrieben, keine echte Supervisor-/HTTP-/AudioWorklet-End-to-End-Ausführung bestätigt. |
| 27.2 / 12.2 | Manifest weiterhin available=false; Registry deaktiviert nicht installierte Modelle; Node-Test mit fehlender/gesperrter Capability und unsicherem Raster. | Modul-/Negativtest geschrieben; gemeinsame Shell noch nicht eingehängt. |
| 27.3 / 12.4 | `python -m unittest discover -s tests -v` (Python 3.11, Node 22). Erster Dokumentationscommit e0337ce: CI-Lauf 45462232932 success. Testcommit a8f6f05: 45462669156 cancelled; Hook-Commit e7f5d39: 45462783834 beim Abruf in_progress. | Gesamtstand nicht als grün bestätigt. |
| 12.3 | `benchmarks/pads/measure.py` (bestehende Render-/Deadline-Vorstufe), `benchmarks/pads/report.py`, `tests/realtime/test_pad_report.py`. | Nicht gemessen. 20 echte Browser-Einsätze und Hörprüfung offen; Auswertung allein ist kein Messaufbau. |

## Nachstellen

- `python -m unittest discover -s tests -v`
- `node --test tests/realtime/pad_wiring.test.mjs tests/realtime/pad_scheduler.test.mjs`
- Nach Einbau des Hooks: 20 echte Pads mit gemessenem E2E-p95, sicherem BeatGrid, Play-Anker
  und Audio-Ausgabe-Messung. Je Job protokollieren: job (1..20), target_frame (ursprüngliche
  Taktgrenze), scheduled_frame (geplanter Einsatz oder null), observed_frame (tatsächlich
  beobachteter Beginn auf derselben korrigierten Quellzeitachse oder null), asset_ready_ms
  (von Anforderung bis dekodiertem Asset). Beobachteten Beginn unabhängig vom Scheduler ermitteln;
  keine Planwerte als Messwerte einsetzen. Hörprüfung und reale BeatGrid-Abweichung separat.
  Format: JSON-Objekt mit Liste jobs. Aufruf:
  `python benchmarks/pads/report.py <baseline.json> <beobachtungen.json> <ergebnis.json>`,
  danach `python -m benchmarks.result <ergebnis.json>`. Der Koordinator bestätigt das Gate
  erst bei mindestens 19/20 rechtzeitigen tatsächlichen Einsätzen und erfolgreicher Hör-/Sicherheitsprüfung.
- Bestehende G1-Messung und Modellinstallationsanweisungen siehe AUFGABE-12 und
  benchmarks/results/g1/stable-audio-3.md. Keine neue Hardwaremessung.

## Versionen, Grenzen, Risiken, Rückbau

- Stable Audio 3 Code MIT: 790793b89ddceea612be9ce42ff6830d18f6fa57; small-music Gewichte
  Stability AI Community License: 8bdfb53c6b0fbc62113cd571fd37373efe15fa14; Gemma-Bedingungen
  prüfen. Python 3.11, Torch/Torchaudio 2.7.1+cu128 im externen Worker, vorhandene Pins
  unverändert. RTX 5080 16 GiB; G1 lookahead grün, keine G3-Messung. Keine neuen Fremdmodule.
- G1-Warmzeit 0,35–0,43 s ist keine E2E-p95. Unbekannte Tonart wird weggelassen; BeatGrid-Schema
  enthält keine Tonart. Begrenztes Stretching über playbackRate verändert Tonhöhe; Hörprüfung offen.
- Backend-Port und Audio-Bridge sind noch nicht produktiv angeschlossen. Keine neue HTTP-Adresse
  oder eingefrorene Vertragsänderung; gemeinsame Dateien und Register/Board unverändert.
- Rückbau: nur eigene Commits revertieren (Merge der Integration nicht rückgängig machen);
  Manifest gesperrt lassen. Keine Originalmusik, Gewichte, Secrets oder Installationen im Repo.

## Übergabe

Fertig: Worker-Dateijob, numerischer Parametervertrag, Pad-Leiste und Audio-Bridge mit Test-Doubles,
Benchmark-Auswertung, WP12-Hook und gepushter Stand.

Offen: KETTE-28-Dateijob auf integration/sirens-rt, persistenter Supervisor-Lifecycle, konkreter
HTTP-/Asset-Backend-Adapter, Shell-/AudioCore-Einbau einschließlich sicherer Tonartbereitstellung,
Ende-zu-Ende-Test, CI-Gesamtstand und 20 echte Einsätze/G3.

Blockade: Der eingesehene Parallelstand extern/KETTE-28 von request_file_job beendet
nach jedem Job den Worker (`self.worker.stop()`). Wiederholte warme Pad-Jobs sind damit nicht
möglich. Änderungen an worker_supervisor.py, routes.py und shell.js sind für diese Kette nicht
zulässig. Der Manifest-Descriptor bleibt deshalb absichtlich gesperrt.

Nächster Schritt: KETTE-28 nach Merge integrieren, sicheren persistenten Dateijob-Pfad oder
expliziten Einmaljob-Modus abstimmen, WP12-Hook umsetzen, komplette E2E-Prüfung inklusive
Abbruch/Lease-Freigabe und G3 ausführen; CI-Fehler beheben.

Lokaler Checkout: `git ls-remote https://github.com/ccogit/Sirens.git refs/heads/extern/KETTE-38`
fehlgeschlagen mit `fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`.
Kein vollständiger lokaler Test. GitHub-API-Push funktioniert. CI zuletzt für ac1e377 noch ohne
Workflow-Run; keine bestätigte Fehlerausgabe der vollständigen CI verfügbar.
