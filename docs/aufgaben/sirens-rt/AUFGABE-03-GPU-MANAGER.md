# Aufgabe 03: GPU-Manager und Worker-Supervisor (WP03)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Kapitel 4 („GPU Manager“, „Model Registry“) und Abschnitt „WP03“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 01 voraus.

## Ziel

Sirens bekommt eine Stelle, die über die GPU wacht und Modell-Worker als eigene Prozesse startet, überwacht und sauber beendet. Kein großes Modell startet ohne Nutzeraktion und ohne zugeteilte Reserve (Lease); bei Engpass gibt es einen klaren Zustand statt Tonaussetzern.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- `sirens/server.py` hat heute eine einfache CUDA-Sperre rund um den Claude-Start; sie bleibt in dieser Aufgabe unverändert.
- `sirens/stems.py` zeigt, wie Sirens heute einen Unterprozess mit eigener Python-Umgebung startet.

## Umfang

1. `sirens/realtime/telemetry.py`: liest GPU-Daten über `nvidia-smi` (Aufruf austauschbar für Tests): VRAM gesamt, belegt, frei, Auslastung, Temperatur; ohne GPU ein gültiger Zustand „keine GPU“.
2. `sirens/realtime/gpu_manager.py`: Lease mit gemessener oder angegebener Peak-Reserve, Sicherheitsreserve (Vorgabe 2,5 GiB, einstellbar), Prioritäten Audio > nächster Abschnitt > Interaktion > Hintergrund > Visuals, Ablehnung mit `busy_gpu`, kontrolliertes Entladen. Fehlt Telemetrie: konservativ sperren. Fremde Prozesse werden nie beendet.
3. `sirens/realtime/worker_supervisor.py`: startet Worker aus einer festen Liste (Allowlist aus der Registry, keine Pfade oder Argumente aus Anfragen), Heartbeat, Zeitlimit, Abbruch, Neustart mit Begrenzung, Beenden des ganzen Prozessbaums unter Windows und Linux, begrenzte Warteschlangen.
4. `sirens/realtime/model_registry.py`: versionierte JSON-Manifeste je Worker unter `workers/<name>/manifest.json` (Capability-Descriptor aus Aufgabe 01, Interpreter aus `.env`, Startparameter); Profile Eco, Performance, Neural, Training/Render.
5. `workers/mock/`: ein Worker ohne fremde Bibliothek, der das IPC aus Aufgabe 01 spricht (Heartbeat, `process`, künstliche Verzögerung, künstlicher Absturz, künstlicher Speicherbedarf) für Tests.
6. `sirens/realtime/routes.py` darf um `GET gpu` und `GET capabilities` (aus der Registry) erweitert werden. Einbau weiterer Stellen als Hook in `docs/realtime/hooks/WP03.md`.

## Nicht im Umfang

- Keine Änderung an der bestehenden CUDA-Sperre in `sirens/server.py` (folgt nach Abnahme durch den Koordinator).
- Kein echtes Modell, kein Torch.
- Kein Audio-Transport (Aufgabe 04), keine Oberfläche (Aufgabe 05).

## Abnahme

1. Tests mit nachgebautem `nvidia-smi`: GPU vorhanden, GPU fehlt, Ausgabe unlesbar → jeweils gültige Telemetrie bzw. konservative Sperre.
2. Tests: Lease wird bei zu wenig freiem VRAM mit `busy_gpu` abgelehnt; höhere Priorität verdrängt niedrigere kontrolliert; externe GPU-Last (Telemetrie ändert sich) führt zu Entladen statt Absturz.
3. Tests mit `workers/mock/`: Start, Heartbeat, Zeitlimit, Abbruch, Absturz mit begrenztem Neustart, gleichzeitige Anfragen, simulierter Speichermangel; nach jedem Test läuft kein Kindprozess mehr.
4. Negativ: Ein Worker-Name außerhalb der Registry und ein Pfad in einer Anfrage werden abgelehnt.
5. Test: `GET /api/rt/v1/gpu` antwortet auch ohne GPU gültig gegen das Schema.
6. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
