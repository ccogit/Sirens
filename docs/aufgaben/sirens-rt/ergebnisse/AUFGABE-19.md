# AUFGABE-19 – Systemabnahme (WP19 / KETTE-51)

## Umfang und Stand

- Windows-Einstieg `benchmarks/suite.ps1`, sequenzieller Runner
  `benchmarks/system_suite.py`, dynamische Registry-/G1-Inventarisierung,
  SHA-256-Prüfung des Originalbestands, Prozessinventar mit PID/Startzeit und
  Nachkontrolle, validierte Sammeldatei nach `benchmarks/result.py`.
- Beispiel-Messplan und frische Rohbericht-Übernahme unter `benchmarks/g4/`,
  Soak-Snippet für 7200 bzw. 1800 Sekunden; Abnahmematrix und Hör-/Störfallanleitung
  in `docs/realtime/abnahme.md`.
- Nur Tests, Messwerkzeuge, Abnahmedokumentation; keine Änderung am Produktcode
  durch WP19. Kein Modell-Download, keine Gate-Entscheidung.
- KETTE-43 und KETTE-28 wurden als echte Mehr-Eltern-Commits eingebunden
  (3833ac73 und 49f90e00). Integrationsstand erneut in ad9e244d gemergt;
  KETTE-43 war bereits im Integrationszweig enthalten (überlappende Blobs identisch),
  der externe Zweig war anschließend nicht mehr vorhanden (404).
  KETTE-28 war bei Nachprüfung vollständig im eigenen Branch enthalten (ahead=0).

## Abnahmepunkte

| Punkt | Beleg / Stand |
|---|---|
| 1 – Störfälle | Neue Tests: `test_system_faults.py` (generiertes Stereo-PCM, Mock-Gain, abgeschnittene Blöcke, Abbruch); `system_faults.test.mjs` (Socket-Wechsel, alter Block verworfen, Dry-Rückfall, Seek-Epoch). Vorhandene Tests unten ergänzen die Störfallabdeckung. |
| 2 – DryRun | `tests/realtime/test_system_suite.py::SystemSuite.test_cli_dry_run` (PowerShell falls verfügbar, sonst identischer Python-Einstieg), `test_dry_run_and_original_change`; Bericht gate=nicht_gemessen. CI des Zwischenstands 4ef554a4 grün (Run 45462783893). |
| 3 – Negativprüfungen | `test_dry_run_and_original_change`, `test_orphan_process`, `test_known_child_survives_parent`: nachgestellte Hashabweichung/neuer Worker führen zu Exitcode 1 bzw. Fehler; PID-Wiederverwendung getrennt. |
| 4 – Hardware/Soak | **Nicht gemessen.** `benchmarks/g4/soak.js`, `benchmarks/g4/report.py`, `benchmarks/g4/plan.example.json`, Aufrufe und Ergebnisformat in `docs/realtime/abnahme.md`. `test_g4_report.py` prüft Dauer und Ergebnisformat ohne Hardware. |
| 5 – Regression | Maßgebliche PR-CI: Zwischenstände cb0413b9 (Run 45462514729), f11fd590 (Run 45462644764) und 4ef554a4 (Run 45462783893) erfolgreich. Endstand-CI bei Erstellung dieses Dokuments noch nicht bestätigt. Board absichtlich unverändert gemäß KETTEN.md. |

### Störfall-Belegmatrix

| Störfall | Test |
|---|---|
| GPU-Engpass / externe Last | `test_gpu_manager.py::GPU.test_leases_and_external_load`, `test_no_gpu_no_action_and_failed_unload` |
| OOM | `test_worker_supervisor.py::Workers.test_oom_and_rejection`, `test_mock_e2e.py::MockHTTP.test_render_backpressure_and_mock_oom` |
| Worker-Absturz | `test_mock_e2e.py::MockHTTP.test_worker_kill_closes_sidecar`, `test_worker_supervisor.py::Workers.test_timeout_restart_and_crash_limit` |
| Verbindungsabbruch | `system_faults.test.mjs` (Mock-Socket/echter RenderPath), `audio_core.test.mjs` (Jitter/Dry) |
| Seek | `test_mock_e2e.py::MockHTTP.test_lifecycle_and_real_worker_pcm`, `audio_core.test.mjs`, `system_faults.test.mjs` |
| Platte voll | `test_recordings.py::RecorderTests.test_disk_full` |
| Ungültige Pfade | `test_mock_e2e.py::MockHTTP.test_wav_resolution_and_recording`, `test_file_jobs.py::FileJobs.test_paths` |
| Origin / Token | `test_audio_sidecar.py::SidecarTests.test_auth`, `test_mock_e2e.py::MockHTTP.test_lifecycle_and_real_worker_pcm` |

## Nachstellen

```powershell
python -m unittest discover -s tests -v
.\benchmarks\suite.ps1 -DryRun
.\benchmarks\suite.ps1 -MusicRoot C:\G4\Synthetisch -Plan C:\TEMP\g4-plan.json -OutputDir C:\TEMP\g4-run-01
python -m benchmarks.result C:\TEMP\g4-run-01\suite.json
```

Hardwareplan vorher gemäß Anleitung anpassen. Ziel: Windows 11 / RTX 5080,
Python 3.11, Node 22, PowerShell. Keine neuen Fremdprojekte, Abhängigkeiten,
Modellrevisionen oder Gewichte; Pins/Lizenzen der Modellketten unverändert.
Lokaler Checkout nicht möglich: `fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`.
Änderungen und Merge-Commits direkt über GitHub; CI maßgeblich.

## Risiken / Abweichungen / Anpassungsbedarf

- G4-Hardwareprüfung nicht gemessen (Auftrag Koordinator). Die Browser-Soak-
  Beobachtung misst digitale Zähler und Zeit, nicht analoge Aussetzer; die
  tatsächliche Performance muss vom Bediener gestartet und durchgängig
  beobachtet werden. Keine vollautomatische Abfolge realer Browser-/Höraktionen.
- Neue freigegebene Registry-IDs werden dynamisch erkannt; ein fehlender
  zugehöriger Messpfad ist ein expliziter Fehler, kein stiller Skip. Für neue
  Modelle muss der jeweilige lokale Messaufruf im Plan ergänzt werden;
  historisch abweichende G1-Dateinamen benötigen ggf. Alias.
- Beispielplan deckt einen Durchgang pro Funktions-ID ab. Alle Profile,
  DSP-Kombinationen, separate Qualitäts-/Hörprüfungen und weitere Messpfade
  der später integrierten Modelle erfordern zusätzliche Läufe/Planeinträge.
  Dies ist eine Abweichung von einer vollständig automatisierten Hardware-Suite.
- Windows-CIM-Prozessüberwachung ist stichprobenbasiert; kurzlebige Eltern
  zwischen Abtastungen bzw. vorab vorhandene Worker erfordern zusätzliche
  manuelle Kontrolle. Kein automatisches Töten fremder Prozesse.
- Stabile G1-Freigaben und tatsächliche Verfügbarkeit sind getrennt; keine
  Freigabe durch WP19. G4 bleibt offen, KETTE-52 bleibt gesperrt.

## Rückbau

Nur WP19-Dateien entfernen bzw. eigene AUFGABE-19-Änderungscommits revertieren;
Voraussetzungsmerges nicht zurücknehmen. Externe Ergebnisordner bei Bedarf
lokal löschen, Musikordner unangetastet lassen.

## Übergabe

**Fertig:** oben genannte CPU-/Mock-Tests, DryRun, sequenzieller Runner mit
Hash-/Prozessprüfungen, dynamischer G1-Inventarisierung und Abnahmematrix,
Soak-Beobachter und Ergebnisvalidierung. Drei Zwischenstände nachweislich grün.

**Offen:** finalen CI-Lauf bestätigen; Beispielplan auf Windows ausführen,
alle freigegebenen Modell- und Profil-Messpfade vervollständigen, reale
2h/30min-Soaks und Hör-/Geräteprüfungen durchführen; Prozesskontrolle auf
Zielrechner verifizieren. G4-Entscheidung ausschließlich durch Koordinator.

**Nächster Schritt:** PR #33 prüfen, ggf. verbleibende CI-Fehler korrigieren,
aktuelle Registry/Integrationsstände erneut prüfen; dann Hardwarelauf anhand
der Abnahmeanleitung und externer, frischer Berichte.

**Fehlerausgabe:** lokaler Git-Zugriff scheitert mit "Could not resolve host:
github.com"; KETTE-43-Ref nach Integration nicht mehr abrufbar (GitHub 404).
Kein bekannter CI-Testfehler in den drei bestätigten Zwischenständen; Endstand
bei Niederschrift noch nicht bestätigt.
