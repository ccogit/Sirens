# Aufgabe 25: Advanced Stem Studio Teil 2 – Dateijob und Verdrahtung (Rest von WP08)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt Aufgabe 08
(Teilstand, gemergt) voraus. Umfang und Abnahme von Aufgabe 08 (`AUFGABE-08-STEM-STUDIO.md`) gelten weiter.

## Ziel

RoFormer-Trennung läuft im Produkt: Song wählen, Trennung als Job starten, Fortschritt sehen, Stems hören und
exportieren; Demucs bleibt Rückfall. Grundlage ist der Dateijob nach `docs/realtime/adr/0006-dateijob.md`.

## Ausgangslage

- Ergebnis und Übergabe von Aufgabe 08: `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-08.md`; vorhandene Module
  `workers/separation/` (`roformer.py`, `models.json`, `requirements.lock`), `sirens/realtime/stem_adapter.py`,
  `web/js/realtime/advanced_stems.js`, Hook `docs/realtime/hooks/WP08.md`.
- Messung: `benchmarks/results/g1/roformer.md` (offline grün, warm RTF 0,038). Funktionierender Lade- und
  Inferenzweg: `benchmarks/spikes/roformer-drumsep/messen.py`, `install.py`.
- Supervisor, GPU-Manager, Registry: `sirens/realtime/worker_supervisor.py`, `gpu_manager.py`,
  `model_registry.py`; Adressen: `sirens/realtime/routes.py`, `sessions.py`.

## Umfang

1. Dateijob nach ADR 0006 in `worker_supervisor.py` und `routes.py` (diese Aufgabe darf beide ändern).
2. `workers/separation/` als echter Worker mit Manifest in der Registry, `install.ps1` nach dem Muster der
   Spikes (Bezug nur nach `-ModelleLaden`), Peak-VRAM-Messung im Worker.
3. `stem_adapter.py`: RoFormer über Dateijob mit GPU-Lease; Demucs-Rückfall bei Fehler oder fehlender
   Installation; Cache-Schlüssel und atomares Veröffentlichen wie in Aufgabe 08.
4. Einbau in die Oberfläche (`advanced_stems.js` in die Lab Shell) und die Adressen (Hook WP08 umsetzen).
5. Messskript `benchmarks/separation/` für einen echten Song (der Koordinator misst).

## Nicht im Umfang

- DrumSep (nicht freigegeben). Keine Änderung an den Adressen von `sirens/stems.py`.

## Abnahme

1. Tests mit nachgebautem Worker: Dateijob läuft, Fortschritt sichtbar, Abbruch löscht `out_dir`, Pfadflucht
   in `source`, `out_dir` und gemeldeten Dateien wird abgelehnt, fremde Datei im Ergebnis abgelehnt, Zeitlimit.
2. Tests: RoFormer-Fehler führt zum Demucs-Rückfall; Cache-Treffer startet keinen neuen Job.
3. `tests/test_stems.py` unverändert grün; CI des PR grün.
