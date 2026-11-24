# AUFGABE-06 – Mock-Durchstich / Gate G2

**Stand: ÜBERGABE, G2 nicht freigegeben.** KETTE-31, Branch extern/KETTE-31, [PR #18](https://github.com/ccogit/Sirens/pull/18), Basis integration/sirens-rt.

## Umsetzung und Prüfbelege

| Bereich | Umsetzung / Beleg | Stand |
|---|---|---|
| Sitzungen, Jobs, GPU | Begrenzte Sitzungs-/Jobverwaltung in sessions.py, WorkerSupervisor, asynchrones Laden, Status, Abbruch, Fehler und Close; GPU-Manager mit konfigurierbarer Reserve, Bestands-Routen und Feature-Flag. HTTP-Tests test_mock_e2e.py. | Kern-CI bestanden; weitere Negativfälle im jüngeren Teststand. |
| Audio / Sidecar | Tatsächlicher Mock-Worker über private IPC und PCM-WebSocket, kurzlebiges einmaliges Token, Origin-Prüfung, begrenzte Renderqueue, Epoch-/Frame-Angaben, Gain/Delay im Worker, Sidecar-Abbau. Test test_lifecycle_and_real_worker_pcm prüft echte WebSocket-Bytes und Worker-Cleanup, test_worker_kill_closes_sidecar prüft Fehlerpfad. | Beide Tests in Lauf 45455157908 erfolgreich; dieser Gesamtlauf war wegen alter WP01-Erwartung rot. |
| Quellen / BeatGrid | Sicherer Pfad über source_path, synthetische Fixture oder PCM16-WAV mit 48 kHz, mono/stereo, maximal 120 s; SHA-256, Read-only PCM-Dekodierung, BeatGrid-Analyse und Cache, GET-Route ohne Neuberechnung; nicht belastbares Grid liefert 503. | Implementiert; erweiterter WAV-/Hash-Test im jüngeren Stand. Andere Formate, RT-Stems und vollständige BeatGrid-/MIDI-Bedienung offen. |
| UI / AudioCore | Lab Shell steuert tatsächliche Sitzungen und Mock-Worker, Dry-Quelle im Browser, Wet über Sidecar, Bypass/Mix/Panic, expliziter Start per Nutzeraktion; bestehender Local Mock nur für Tests. JS-Tests in mock_e2e.test.mjs. | Implementiert; Browser-/Geräteprüfung offen. |
| DSP | Optionaler, standardmäßig deaktivierter RackPath im AudioCore/Worklet; Parameter-, Preset- und Reset-Hooks, vorhandener Limiter bleibt. | Keine DSP-Freigabe und keine vollständige DSP-Bedienoberfläche. |
| Recorder | Sessiongebundene Recorder- und Export-Routen, begrenzter Upload, Abschluss, separate Ablage, Quota/Reservierung, Reparatur bei Initialisierung, Hashprüfung beim Export, UI-Aufnahme. | Implementiert; neue HTTP-Prüfung im jüngeren Stand; vollständiges Replay, Hash-Neuprüfung beim Replay und Recovery im realen Betrieb offen. |
| Fehler / Sicherheit | Tests für Feature-Flag, Origin, falsches Token, Stale Epoch, Worker-Kill und Cleanup; weitere Tests für Backpressure, OOM über echten Mock-Worker, ungültiges PCM und zu großen HTTP-Body hinzugefügt. Keine Test-Fehler-Endpunkte im Produkt. | Jüngste CI separat prüfen; lokale Tests nicht ausführbar. |
| G2 | benchmarks/g2/soak.js, report.py und README.md: 30-Minuten-Messung mit echtem Worker/Sidecar/Core, PCM-Vergleich, Underruns, expliziter Worker-Kill und Dry-Fallback, Ergebnisformat. | Nicht ausgeführt; tatsächliche Master-/Geräteausrichtung, UI-Loop/Seek und 30-Minuten-Lauf nicht nachgewiesen. |

## CI und Umgebung

- [45454638045](https://github.com/ccogit/Sirens/actions/runs/45454638045): erster Commit erfolgreich.
- [45454926865](https://github.com/ccogit/Sirens/actions/runs/45454926865), [45455157908](https://github.com/ccogit/Sirens/actions/runs/45455157908): alter Platzhaltertest in tests/realtime/test_rt_contracts.py erwartete HTTP 503 für ungültigen Session-Request, der nun vertragsgemäß HTTP 400 liefert. Fehler: AssertionError: 400 != 503 (Zeile 183). Einzige Änderung an dieser Altprüfung: Erwartung auf 400 invalid angepasst.
- [45455925791](https://github.com/ccogit/Sirens/actions/runs/45455925791): **success**, Commit 1c42777c443dddf53312f4472fca4eaab1f7e36c, einschließlich der wesentlichen Integrationsänderungen.
- [45456074422](https://github.com/ccogit/Sirens/actions/runs/45456074422) und [45456289941](https://github.com/ccogit/Sirens/actions/runs/45456289941): durch nachfolgende Commits abgebrochen.
- [45456329401](https://github.com/ccogit/Sirens/actions/runs/45456329401): beim Schreiben dieser Datei in Bearbeitung, Commit 1c6357764fe908e97a08baa0f123467785c4ed00. Kein grüner Nachweis für den letzten Stand behauptet.
- Vollständiger lokaler Checkout nicht möglich: git meldete `Could not resolve host: github.com`. Änderungen wurden unmittelbar über GitHub gepusht. Maßgeblich ist die PR-CI, keine lokalen Testresultate behauptet.
- Integrationsstand 316a225fddddc618adc7e84d14056806d559483f über Merge f2687519eaf162be8b30a2fd3c017077baa547d2 eingebunden, kein Force-Push. Register, Board und Dateien der parallelen KETTE-37 nicht bearbeitet.

## Abweichungen / offene Risiken

- Der Durchstich ist ein begrenzter CPU-Mock-Referenzpfad für WAV/48 kHz. Zeitadressierte Befehle, RT-Stems, beliebige Dateiformate/Raten, vollständige BeatGrid-Quantisierung/MIDI-Anbindung und Session-Replay sind nicht fertig. Keine Echtzeit- oder Modellfreigabe.
- Zusätzliche, vom eingefrorenen Kernschema getrennte Transport-/Render-/Dry- und Asset-Auflösungsrouten verbinden Browser und Session; Vertragskompatibilität und Sicherheitsprüfung dieser Integrationsentscheidungen durch den Koordinator erforderlich.
- DSP bleibt aus; vollständige DSP-Controls, Delay-Kompensation sowie GUI-/Audioverifikation fehlen. GPU-Queue-Telemetrie ist teilweise aggregiert; CPU-Mock ersetzt keine reale GPU-Lastmessung.
- Recorder-Quota, Recovery nach Prozessabbruch, Session-Close bei laufendem Upload und Cleanup unter Fehlerlast sind im echten Betrieb noch zu prüfen.
- Audio-Epoch-/Master-Frame-Zuordnung bei Loop, Seek, Pause, verspäteten Wet-Blöcken und Dry-Fallback muss mit realem Browser geprüft werden. Digitale PCM-Deckung allein ist kein Nachweis für die Geräteausrichtung.
- 30-Minuten-Soak, realer Worker-Kill im Browser und Messbericht fehlen. G2 bleibt offen.

## Übergabe

**Fertig:** Kernintegration, reale Mock-Worker- und Sidecar-Kommunikation, sichere WAV-Quellen, BeatGrid-/Recorder-Adressen und UI-Anbindung, DSP-Hook, Tests und Messharness gepusht. Ein früherer Integrationsstand ist in der CI grün.

**Offen:** Letzten CI-Lauf prüfen und gegebenenfalls korrigieren; die genannten unvollständigen Bedien-/Scheduling-/Replay-Pfade schließen, Browser-/Master-Frame- und Recorder-Lifecycle prüfen und G2-Messung durchführen.

**Nächster Schritt:** PR-CI prüfen; danach den Ablauf in benchmarks/g2/README.md mit aktiviertem Mock durchführen, Rohdaten und WP00-Bericht sichern, den tatsächlichen Audio-Master bei Loop/Seek und Worker-Kill prüfen. Erst nach den vollständigen Abnahmekriterien G2 freigeben. Keine Freigabe allein aufgrund des grünen Zwischenstands.

**Fehlerausgabe:** lokal `Could not resolve host: github.com`; frühe CI `AssertionError: 400 != 503` in test_rt_contracts.py (korrigiert). Jüngster CI-Stand zum Zeitpunkt der Übergabe noch nicht abschließend belegt.

**Rollback:** PR nicht mergen bzw. ausschließlich die KETTE-31-Änderungen im Integrationszweig revertieren; keinen Force-Push verwenden. Laufzeitseitig SIRENS_RT_ENABLED=0; separate RT-Aufnahmen/Exports nicht automatisch löschen.
