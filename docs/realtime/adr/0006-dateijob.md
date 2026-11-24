# ADR 0006: Dateijobs für Offline-Worker

Status: angenommen (Koordinator, 24.11.2026). Erweitert ADR 0003 (Worker-IPC); ändert nichts an bestehenden
Nachrichten.

## Kontext

Offline-Modelle (Trennung mit RoFormer, später SAM Audio, Rendern mit Stable Audio) verarbeiten ganze
Songdateien. `WorkerSupervisor.request` erlaubt nur die Arten `probe`, `load`, `warmup`, `process`, `health`,
`unload`, keine Pfade und höchstens 1 MiB PCM je Nachricht. Ein Song passt nicht hinein; Pfade aus Anfragen sind
verboten (README Abschnitt 4 Punkt 9).

## Entscheidung

1. Neue Nachrichtenart `file_job` am Supervisor: `request_file_job(job_id, source, out_dir, params, timeout)`.
2. `source` und `out_dir` setzt **ausschließlich der Server**: `source` über `safe_audio_path` unter dem
   Musikordner oder ein Asset-Pfad unter dem Echtzeit-Cache, `out_dir` ein neu angelegter Ordner unter
   `cfg.realtime_dir / "jobs" / <job_id>`. Aus HTTP-Anfragen kommen nur Asset-ID bzw. Songpfad relativ zum
   Musikordner, nie absolute Pfade.
3. Der Worker liest `source`, schreibt nur nach `out_dir`, meldet Fortschritt über den Heartbeat und am Ende eine
   Liste erzeugter Dateien (relativ zu `out_dir`). Der Supervisor prüft, dass jede gemeldete Datei in `out_dir`
   liegt, und veröffentlicht atomar (Ordner umbenennen).
4. `params` nur aus den Controls des Capability-Descriptors (wie bei `load`). GPU-Lease wie bei `process`;
   Abbruch beendet den Prozessbaum und löscht `out_dir`.
5. Jobs laufen asynchron über die bestehenden Adressen `GET jobs/{id}` und `POST jobs/{id}/cancel`; Ergebnisse
   werden zu Assets (`GET assets/{id}`).

## Folgen

`worker_supervisor.py` und `routes.py` bekommen je eine Ergänzung, dazu Tests für Pfadflucht, fremde Dateien im
Ergebnis, Abbruch und Zeitlimit. Bestehende Verträge bleiben gültig.
