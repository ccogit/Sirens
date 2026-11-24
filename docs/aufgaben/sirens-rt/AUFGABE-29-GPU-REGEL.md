# Aufgabe 29: GPU-Regel, Profile und dauerhafter Supervisor

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt die gemergten
Aufgaben 03, 17/26, 25 und 27 voraus.

## Ziel

Mehrere Modelle, Claude-Läufe und die Visualisierung teilen sich die RTX 5080 kontrolliert: kein Absturz, kein
Tonaussetzer durch fremde Last, klare Busy-Zustände.

## Ausgangslage

- `sirens/realtime/gpu_manager.py`, `worker_supervisor.py`, `model_registry.py`, `telemetry.py`; alte
  CUDA-Sperre beim Claude-Start in `sirens/server.py`.
- Gemessene Speicherbedarfe: `benchmarks/results/g1/roformer.md`, `stable-audio-3.md` (Prozess ~1,7–2,6 GiB);
  Manifeste unter `workers/*/manifest.json` (`vram_peak_bytes`).
- Offene Punkte: `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-26.md` (Claude-Konkurrenz, Profile mit
  Supervisor-Queues) und `AUFGABE-27.md` (persistenter Supervisor-Lebenszyklus).

## Umfang

1. Claude-Start und laufende Sitzung über den GPU-Manager regeln (Lease für Claude-Läufe mit konservativem
   Budget, auch für automatische Folgeläufe); die alte CUDA-Sperre bleibt als Rückfall ohne Telemetrie.
2. Persistente Worker je Sitzung (Vorladen nach Nutzeraktion, Aufwärmen, Entladen bei Verlassen oder
   Speicherdruck), Prioritäten aus `PLAN.md` Kapitel 4.
3. Profile Eco, Performance, Neural, Training/Render mit Wirkung auf Supervisor-Queues, gleichzeitig geladene
   Modelle und Visualisierung.
4. Telemetrie-Anzeige (bestehendes `gpu_panel.js`) mit Lease-Liste.

## Nicht im Umfang

- Oberflächen-Einbau der Modul-Hooks (Aufgabe 28, parallel); nur `gpu_panel.js` darf hier angepasst werden.

## Abnahme

1. Tests mit nachgebautem `nvidia-smi` und Mock-Workern: Claude-Start bei voller Lease wird abgelehnt oder
   verdrängt niedrigere Priorität kontrolliert; ohne Telemetrie konservativ; kein verwaister Prozess.
2. Tests: Profilwechsel ändert Queue-Grenzen und Anzahl geladener Modelle.
3. CI des PR grün.
