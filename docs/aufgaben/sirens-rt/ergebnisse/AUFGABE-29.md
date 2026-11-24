# AUFGABE-29 – GPU-Regel, Profile und Supervisor – ÜBERGABE

Depends-on: WP03, WP17/26, WP25, WP27. Basis nach Zweieltern-Merge:
1637a21acf4dd79dffecc0f255b9125726c0d7c0. Ziel integration/sirens-rt, kein Force-Push.
PR #34. Kein neues Modell freigegeben.

## Umgesetzt

- Exklusive Claude-Lease mit konservativer, nicht gemessener 8-GiB-Admission plus vorhandener Reserve.
  Bei aktiven Modell-Leases oder zu wenig freiem VRAM Ablehnung; keine fremden Prozesse beenden.
  Bei fehlender Telemetrie darf Claude ausschließlich ohne andere Leases starten;
  neue RT-GPU-Worker bleiben gesperrt. Claude-Läufe und vorgemerkte Folgeläufe behalten
  dieselbe Lease; Freigabe nach Ende bzw. fehlgeschlagenem Start. Manueller Start: busy_gpu/409;
  automatische Übergabe: Fehler im Starter-Zustand, bereits ausgeführte Nutzeraktion bleibt erhalten.
- Bei RT-Flag nutzt server.py die vorhandene routes.service()-Instanz auch für Claude und Legacy-CUDA.
  Legacy-Sperre bleibt bestehen. Demucs-CUDA bekommt eine exklusive Lease bis der vorhandene
  StemDienst keinen aktiven Job mehr meldet. Bei Flag aus bleibt die alte Policy unverändert.
- WorkerSupervisor liest globale Profilgrenzen für neue Requests, zusätzliche feste Limits
  bleiben als Obergrenze. Queue-Downgrade verwirft keine bereits angenommenen Requests.
  GPU-Profilgrenzen wie in WP26: 0/1/2/1; bei zu vielen aktiven Leases kein erzwungener Audio-Abbruch.
- SessionWorkers: explizites Vorladen/Load/Warmup, Wiederverwendung lebender Prozesse,
  Entladen/Close; kein selbständiger Modellstart. Bestehende Prioritäten und GPU-Reconcile.
  Der Pool ist ein Modul mit Hook, noch nicht produktiv in Sessions angeschlossen.
- Lease-Diagnose als getrennte Liste (ID, Besitzer, Budget, Priorität); gpu_panel.js stellt sie
  auch ohne Telemetrie dar. Keine Änderung des eingefrorenen Telemetrie-Schemas.
  Routen- und Shell-Einbau sowie Visual-Drosselung: WP29-Hook für KETTE-44.

## Abnahme

| Punkt | Beleg | Stand |
|---|---|---|
| 29.1 | tests/realtime/test_gpu_rule_29.py: nachgebautes nvidia-smi, volle Audio-Lease, Busy-Code, fehlende Telemetrie, CPU-Prozess als Claude-Double mit Folgelauf, Mock-Worker nach Close beendet. | Tests implementiert; vollständiger CI-Nachweis offen. Kein echter Claude-/GPU-Lauf. |
| 29.2 | test_gpu_rule_29.py: Queue-Limits 4/8/2 am bereits gestarteten Mock-Supervisor, zwei Leases in Neural, abgelehnter Downgrade, Eco-Sperre. Bestehende test_gpu_profile_26.py und test_worker_supervisor.py prüfen Admission und Queue. | Teilweise: dynamische Grenzen und Pool implementiert; echter Modell-Multiplex und Visualisierung nicht gemessen. |
| 29.3 | tests/realtime/gpu_panel_29.test.mjs: Lease-Anzeige bei fehlender Telemetrie und leere/unbekannte Liste. | Test geschrieben; UI-Hook noch nicht produktiv ausgeführt. |
| CI | `python -m unittest discover -s tests -v` (Python 3.11, Node 22). CI 45465911305, 45466199158 und 45466255913 durch neuere Commits abgebrochen; CI 45466318933 beim letzten Abruf in_progress. | Abschließender Gesamtstand nicht als grün bestätigt. |

## Nachstellen / Grenzen

- `python -m unittest discover -s tests -v` und `node --test tests/realtime/gpu_panel_29.test.mjs`.
- Zielrechner: `python -m sirens.realtime.telemetry` liefert JSON-Telemetrie; danach in einer
  Testinstallation mit RT-Flag kontrolliert Claude-Start, Modell-Lease, Profilwechsel,
  Panic/Close und fehlendes nvidia-smi prüfen. Keine echte Hardwaremessung oder Hörprüfung
  in dieser Bearbeitung; 8 GiB sind eine konservative Policy-Annahme, kein gemessener Peak.
  Ein automatisierter Hardware-/Audio-Soak-Messpfad für WP29 fehlt noch.
- Python 3.11 Standardbibliothek, ES-Module, Node 22. Keine neuen Fremdprojekte, Pins,
  Gewichte oder Lizenzen. Bestehende Manifeste und Freigaben unverändert.
  Ziel: Windows 11, RTX 5080 16 GiB. Kein fremder Prozess wird durch GPUManager beendet.
- Konservativ exklusiv statt gleichzeitiger Claude-/RT-GPU-Produktion; VRAM-Budget kann
  Starts unnötig sperren. Externer GPU-Verbrauch und Claude-Unterprozesse außerhalb der
  beobachteten Starter-Sitzung sind nicht zuverlässig erfasst. Windows-Prozessbaum und
  realer Legacy-Demucs-Lifecycle sind nicht verifiziert.
- Der bisherige Datei-Job-Modus beendet den Worker vor Veröffentlichung, um spätere
  Schreibzugriffe auf veröffentlichte Assets zu verhindern. Er bleibt unverändert;
  persistente warme Datei-Jobs (insbesondere Pads) sind noch offen. Der Pool für
  Chunk-/Streaming-Pfade ist davon getrennt.
- Gemeinsame Routen/Sessions/Shell nicht geändert. server.py nur für CUDA-/Claude-Admission
  angepasst. Register nur durch Merge der Integration übernommen, Board unangetastet.

## Übergabe

**Fertig:** GPU-Admission, Claude-Lease über Folgeläufe, dynamische Queue-Limits,
Vorladungs-/Sitzungspool als Modul, Lease-Text und Hook, Mock-Tests, gepushter Stand.

**Offen:** CI-Gesamtstand, HTTP-Integrationstests der neuen Claude-/CUDA-Regel,
produktiver Pool-Einbau einschließlich Panic/Close, separater Lease-Endpunkt und Shell-Poll
(KETTE-44/Koordinator), sichere persistente Dateijobs, reale Windows-/RTX- und Visual-Abnahme.
Kein vollständiger WP29-Abnahmenachweis.

**Nächster Schritt:** finale CI abrufen und etwaige Fehler korrigieren; WP29-Hooks mit
KETTE-44 zusammenführen, einen sicheren persistenten Datei-Job-Veröffentlichungspfad
vereinbaren und testen, Prozessbaum-/GPU-Soak auf Zielhardware durchführen.

**Fehlerausgabe/Blockade:** Lokaler Checkout mit
`git ls-remote https://github.com/ccogit/Sirens.git refs/heads/extern/KETTE-45` scheitert:
`fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`.
Lokal Python 3.13.5 und Node v22.16.0 statt gefordertem Python 3.11.
GitHub-API-Push/PR funktionieren. Keine bestätigte CI-Fehlerausgabe des letzten Stands;
CI noch nicht abgeschlossen. Restumfang nicht vollständig umgesetzt.

**Rollback:** PR nicht mergen bzw. nur eigene Änderungen revertieren, nicht den
Upstream-Merge zurücknehmen. Kein Force-Push. SIRENS_RT_ENABLED aus erhält Bestands-Policy.
Keine Originaldateien oder Modellgewichte löschen.
