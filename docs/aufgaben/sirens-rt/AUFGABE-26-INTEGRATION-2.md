# Aufgabe 26: Produktintegration Teil 2 (Rest von WP17)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt Aufgabe 17
(Teilstand, gemergt) voraus. Umfang und Abnahme von Aufgabe 17 (`AUFGABE-17-INTEGRATION.md`) gelten weiter,
außer der Stem-Trennung (macht Aufgabe 25 parallel).

## Ziel

Die Performance-Suite ist vollständig bedienbar und verhält sich auf der GPU vernünftig neben Claude-Läufen und
der Visualisierung.

## Ausgangslage

- Ergebnis und Übergabe von Aufgabe 17: `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-17.md` (offen:
  GPU-Regel und Claude-Konkurrenz, GPU-Profile und Visual-Drosselung, Bedienung von DSP-Rack und
  Performance-Tools, Automation, vollständiger E2E-Ablauf).
- Hooks: `docs/realtime/hooks/WP09.md`, `WP14.md`; Module unter `web/js/realtime/` und `sirens/realtime/`.
- Alte CUDA-Sperre beim Claude-Start in `sirens/server.py`; GPU-Manager `sirens/realtime/gpu_manager.py`.

## Umfang

1. GPU-Regel: Der GPU-Manager ersetzt die alte CUDA-Sperre beim Claude-Start; ohne Telemetrie konservativ wie
   bisher.
2. Profile Eco, Performance, Neural, Training/Render in Oberfläche und Manager; die Visualisierung drosselt im
   Neural-Profil zuerst.
3. Bedienung von DSP-Rack (WP09) und Performance-Tools (WP14) in der Lab Shell nach ihren Hooks.
4. Parameter-Automation und Presets über alle Module; Panic überall wirksam.
5. Durchgehender Ablauf mit Mock und, wo installiert, echten Workern: Song laden, Stems wählen, Effekt
   einschalten, Pad auslösen (Mock, solange Aufgabe 12 läuft), aufnehmen, exportieren, stoppen.

## Nicht im Umfang

- `workers/separation/`, `sirens/realtime/stem_adapter.py`, `advanced_stems.js`, Dateijob im Supervisor
  (Aufgabe 25). `workers/stable_audio/`, `pad_scheduler.js` (Aufgabe 12). Katalog-API und Song-/Albumliste.

## Abnahme

1. Tests: Claude-Start während laufender Sitzung folgt der GPU-Regel; ohne Telemetrie konservativ.
2. Tests: Profilwechsel wirkt auf Manager und Visualisierung; Panic stoppt alle Module.
3. Tests für den durchgehenden Ablauf (Node und HTTP) mit Mock; kein Leck nach Verlassen.
4. CI des PR grün.
