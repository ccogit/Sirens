# AUFGABE-03 – GPU-Manager und Worker-Supervisor (WP03)

KETTE-21, [PR #10](https://github.com/ccogit/Sirens/pull/10), Basis integration/sirens-rt. Depends-on KETTE-11: von 9e1ae563 gestartet, Voraussetzung zunächst per Fast-Forward 05592a62 übernommen, dann erneut per Merge 8c726657 auf 7f69f454 aktualisiert. KETTE-11 wurde zwischenzeitlich gemergt und ihr Branch gelöscht; Integrationsstand b229e233 und anschließend ae58b386 übernommen. Register/Board-Änderungen ausschließlich geerbt, keine eigenen.

## Umsetzung

- telemetry.py: nvidia-smi per austauschbarem Runner, Gerät 0, zwei Sekunden Timeout, MiB in Bytes; fehlende/ungültige Ausgabe ergibt gültigen nicht verfügbaren Zustand. Freier VRAM intern, HTTP genau eingefrorenes Schema.
- gpu_manager.py: atomare Peak-Leases, 2,5 GiB konfigurierbare Sicherheitsreserve, fünf Prioritätsstufen, nur eigene bestätigte Entladung, externe Last per reconcile(), konservative doppelte Anrechnung der Peaks (keine sichere Prozesszuordnung). Profilgrenzen begrenzen Zahl der GPU-Leases.
- model_registry.py: lokale versionierte Manifeste, Capability-Validierung, erlaubte Worker-Namen und lokale Interpreter aus .env; Eco/Performance/Neural/Training/Render; keine Downloads. Mock explizit aktivierbar, CPU und offline.
- worker_supervisor.py und workers/mock/: persistenter Prozess, Längenpräfix uint32 LE + JSON v1, getrennte begrenzte Float32-Binärdaten, Heartbeat 1 s / 3 s Ausfallgrenze, begrenzte gleichzeitige Anfragen, Deadline, Abbruch mit kurzer kooperativer Frist, begrenzter CPU-Neustart ohne Wiederholung oder implizites Laden. GPU-Start nur mit Nutzeraktion/Lease; Linux-Prozessgruppe und Windows-JobObject (KILL_ON_JOB_CLOSE). Mock Gain/Delay, künstliche Verzögerung, OOM und Absturz. Keine Modellbibliothek im Hauptprozess.
- GET gpu und GET capabilities angebunden; Flag und Origin-Prüfung beibehalten. Einbau weiterer Stellen (periodisches reconcile, Session-/Dienst-Shutdown, Zähler, Dry-Fallback) in docs/realtime/hooks/WP03.md. Bestehende CUDA-Sperre unverändert.

## Abnahme

CI [Lauf 45453073282](https://github.com/ccogit/Sirens/actions/runs/45453073282), Code-Head 31c66933: 112 Tests, 1 Fehlschlag, 4 bestehende Skips; alle elf neuen WP03-Tests ok. Vorlauf [45452875075](https://github.com/ccogit/Sirens/actions/runs/45452875075): 110 Tests, 1 Fehlschlag, 4 Skips, alle neun damaligen WP03-Tests ok.

| Nr. | Beleg | Stand |
|---|---|---|
| 1 | GPU.test_telemetry, GPU.test_no_gpu_no_action_and_failed_unload: Fake-SMI, fehlende/unlesbare Ausgabe, Schema und Sperre | CI ok |
| 2 | GPU.test_leases_and_external_load, test_concurrent_admission_and_profile, test_no_gpu_no_action_and_failed_unload: busy_gpu, Verdrängung, externe Last, verweigerte Freigabe, konkurrierende Zuteilung, Profilgrenze | CI ok |
| 3 | Workers.test_heartbeat_and_persistent_process, test_timeout_restart_and_crash_limit, test_concurrent_and_cancel, test_bounded_queue, test_oom_and_rejection: echte CPU-Unterprozesse, Gain, Warmup, Heartbeat, Deadline, Cancel, Crash, Neustartlimit, Queue, simuliertes OOM; Cleanup prüft gestartete Mock-Prozesse | CI ok; Windows und separate Enkelprozesse nicht geprüft |
| 4 | Workers.test_oom_and_rejection: ../mock, path im Load-Payload, Start ohne Nutzeraktion, Mock-Flag | CI ok |
| 5 | GPURoutes.test_gpu_without_gpu_and_flag, test_registry: 200 ohne GPU, Schema, Flag 503, Origin 403, Registry | CI ok |
| 6 | python -m unittest discover -s tests -v | CI rot: ausschließlich veraltete Erwartung im WP01-HTTP-Test, siehe Übergabe. Board durch Koordinator. |

## Anpassungsbedarf

- WP01-Test tests/realtime/test_rt_contracts.py, HTTP.test_switch_and_security, erwartet nach Aktivierung noch GET gpu -> 503. WP03 verlangt ausdrücklich 200 mit Telemetrieschema auch ohne GPU. Test gehört KETTE-11; nach KETTEN.md nicht selbst ändern. Koordinator soll die alte Erwartung durch 200 + validate("telemetry", body) ersetzen (bei deaktiviertem Flag weiterhin 503). Keine Laufzeit-Sonderbehandlung für Tests.
- WP01 hat schema.py in schemas/__init__.py umbenannt; eigene Imports beim Merge angepasst.
- Reale Modelladapter müssen die Binär-IPC-Konvention, festen Startparameter und numerischen Capability-Controls übernehmen; weitere Nutzdaten erst mit vereinbartem Vertrag. Die GPU-Manager-/Supervisor-Instanzen und periodisches reconcile werden in WP06 eingebunden; GET gpu liefert bis dahin Snapshot mit Zählern 0.

## Grenzen, Hardware und Rückbau

Python 3.11 Standardbibliothek, Node 22 für Bestandstests. Keine Fremdprojekte, Modellgewichte, weiteren Lizenzen oder Commit-Pins; Mock unter Repo-Lizenz. Keine GPU nötig für CPU-Tests. Vollständiger lokaler Checkout/Tests nicht durchgeführt; CI maßgeblich.

Zielhardware RTX 5080 / Windows 11 **nicht gemessen**. Nachstellen: `python -m unittest discover -s tests -v`; gezielt `python -m unittest discover -s tests -p "test_gpu*.py" -v` und `python -m unittest discover -s tests -p "test_worker_supervisor.py" -v`. Auf Zielrechner `python -m sirens.realtime.telemetry` liefert JSON mit device, available, vram_total_bytes, vram_used_bytes, vram_free_bytes, compute_percent, temperature_c. Unter realer Fremdlast erneut ausführen. Keine Aussage über Audioaussetzer oder gemessene Reserve: WP06/G2 und G3 müssen das belegen. Windows-JobObject-Cleanup und gezielt erzeugte Enkelprozesse sind noch separat zu prüfen; vertrauenswürdige Worker dürfen vor Job-Zuordnung keine eigenen Kinder starten und Linux-Worker dürfen nicht aus ihrer Prozessgruppe ausbrechen. Der Supervisor gibt GPU-Leases beim close() oder kontrollierter Verdrängung frei; bei GPU-Crash muss der Session-Layer close() garantieren. Kein echter GPU-Worker installiert/freigegeben. Peak-Doppelanrechnung kann unnötige Ablehnungen erzeugen; bewusst konservativ. Kein Modellstart durch GET.

Rückbau: Flag aus; WP03-eigene Änderungen revertieren, geerbte Integrations-/KETTE-11-Commits nicht rückgängig machen; kein persistiertes Modellmaterial.

## Übergabe

Fertig: WP03-Implementierung, elf neue Tests (CI bestanden), Hook und Ergebnisdatei, gepushter Stand. Offen: Gesamt-CI grün, Windows-/Enkelprozess-Cleanup und Hardware-/Audio-Nachweis, Session-Einbau gemäß Hook.

Nächster Schritt für Koordinator: WP01-HTTP-Test an WP03 anpassen, dann Gesamt-CI erneut ausführen und erst nach Prüfung mergen. Keine Änderung am Register oder Board durch KETTE-21.

Fehlerausgabe CI (Lauf 45453073282): `FAIL: test_switch_and_security (realtime.test_rt_contracts.HTTP.test_switch_and_security)`; `self.assertEqual(self.http("GET","/api/rt/v1/gpu")[0],503)`; `AssertionError: 200 != 503`; `Ran 112 tests in 17.416s`; `FAILED (failures=1, skipped=4)`. Nach dem Code-CI-Lauf ausschließlich Integrationsstand und dieses Ergebnis übernommen; neuer Head-CI-Lauf separat zu prüfen.
