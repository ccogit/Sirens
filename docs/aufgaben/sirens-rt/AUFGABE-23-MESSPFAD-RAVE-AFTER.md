# Aufgabe 23: Lauffähiger Messpfad RAVE und AFTER (Rest von WP02)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt Aufgabe 21 voraus
(gemergt). Umfang je Kandidat wie in `docs/aufgaben/sirens-rt/AUFGABE-21-SPIKES-MESSPFADE.md`, Abschnitt
„Umfang“, Punkte 1 bis 6; diese Aufgabe gilt nur für RAVE und AFTER.

## Ziel

Der Koordinator kann RAVE und AFTER am Zielrechner mit genau kopierbaren Befehlen installieren und mit echter
Inferenz messen. Das Gate G1 schaltet KETTE-34 frei.

## Ausgangslage

- Bericht und bisherige Dateien: `benchmarks/spikes/` (Ordner des Kandidaten), Messhilfe
  `benchmarks/spikes/runner.py`, `common.py`.
- Vorbild für einen fertigen Pfad: `benchmarks/spikes/roformer-drumsep/` (`requirements.lock`, `weights.json`,
  `install.ps1`, `install.py`, `messen.py`) und die Messung `benchmarks/results/g1/roformer.md`.
- Erfahrungen vom Zielrechner (Windows 11, RTX 5080, Python 3.11): Torch 2.7.1+cu128 läuft (`sm_120`); Pakete,
  die beim Installieren C/C++ bauen (z. B. `diffq` über `demucs`), scheitern ohne Build-Tools – nur Wheels
  verwenden oder Alternative nennen.
- RAVE: vortrainierte Modelle mit geprüfter Lizenz (TorchScript nur mit Hash), Streaming-Latenz je Block. AFTER: gepinntes Audio-to-Audio-Beispiel, lokaler vertrauenswürdiger Export.

## Umfang

1. Pins in `requirements.lock`, Gewichte in `weights.json` (URL, Datei, Größe, SHA-256, Lizenz), sicherer Loader.
2. `install.ps1`/`install.py` mit Bezug nur nach `-ModelleLaden` und Bestätigung, Hash-Prüfung.
3. `messen.py` mit echter Inferenz über `benchmarks/spikes/runner.py`; bei Streaming RTF je Block.
4. Benötigt das Modell einen Zugang (Login, Lizenzbestätigung): genau benennen, welcher Schritt beim Nutzer
   liegt, mit Link. Bericht ergänzen; Eintrag in `benchmarks/spikes/README.md`.

## Nicht im Umfang

- Keine Messung, kein Gate. Keine Gewichte im Repo. Nichts unter `sirens/`, `web/`, `workers/`.

## Abnahme

1. `messen.py --dry-run` läuft; `weights.json` hat die Pflichtfelder; kein Bezug ohne Schalter; kein unsicherer
   Loader (bestehender Test `tests/realtime/test_spike_weight_safety.py` bleibt grün).
2. CI des PR grün.
