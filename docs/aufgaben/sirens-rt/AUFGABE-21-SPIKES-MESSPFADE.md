# Aufgabe 21: Modell-Spikes Teil 2 – lauffähige Messpfade (Rest von WP02)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP02“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 02 voraus (gemergt als Teilstand).

## Ziel

Aufgabe 02 hat zehn Quellenberichte, eine Messbasis und drei experimentelle Messskripte geliefert, aber noch
keinen Weg, auf dem der Koordinator am Zielrechner ein Modell installieren und messen kann. Diese Aufgabe macht
die Messpfade lauffähig, in dieser Reihenfolge, weil davon gesperrte Ketten abhängen:

1. RoFormer/DrumSep (schaltet KETTE-26 frei)
2. SAM Audio (KETTE-27)
3. Stable Audio 3 (KETTE-35)
4. RAVE und AFTER (KETTE-34)
5. DEMON (KETTE-33)
6. Magenta RealTime (KETTE-36, optional)

Lieber die ersten drei vollständig als alle sechs halb. Was nicht fertig wird, steht in der Übergabe.

## Ausgangslage

- `benchmarks/spikes/<kandidat>/BERICHT.md`: Quellenlage, Lizenzen, Risiken, Messplan je Kandidat, mit offenen
  Punkten (Pins, Hashes, Größen, Gewichtslizenzen).
- `benchmarks/spikes/common.py`, `benchmarks/spikes/runner.py`: Messhilfe (Zeit, Perzentile, RTF, VRAM-Sampling,
  Ergebnis schreiben). Tests: `tests/test_spike_common.py`, `tests/test_spike_runner.py`.
- `benchmarks/spikes/<kandidat>/install.ps1`: eigene Umgebung `.venv-spike-<kandidat>`; der Modellbezug ist
  noch absichtlich gesperrt („Pins und Hashes fehlen“).
- `messen.py` gibt es nur für RAVE, Stable Audio 3 und SAM Audio.
- Ergebnisdatei der Vorgängerin: `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-02.md`, Abschnitt „Übergabe“.

## Umfang

Je Kandidat in der Reihenfolge oben:

1. **Feste Pins:** in `benchmarks/spikes/<kandidat>/requirements.lock` (oder gleichwertig) die genauen
   Paketversionen inklusive PyTorch-Build für CUDA 12.8 (RTX-50-Reihe); Commit des Projekt-Repos.
2. **Gewichte:** je Modell Bezugsquelle (URL), Dateiname, Größe, SHA-256 und Lizenz in
   `benchmarks/spikes/<kandidat>/weights.json`. Wo Größe oder Hash aus der Quelle nicht hervorgehen: im
   Skript beim ersten Bezug berechnen und in eine lokale Datei schreiben, dem Nutzer vorher Quelle und Lizenz
   zeigen. Nur sichere Formate laden (safetensors, oder `torch.load(..., weights_only=True)`); wo das Projekt
   unsicher lädt, einen eigenen sicheren Loader im Messskript.
3. **`install.ps1`** gibt den Bezug frei, sobald 1 und 2 stehen: ohne `-ModelleLaden` nichts herunterladen;
   mit `-ModelleLaden` Quelle, Größe und Lizenz zeigen, nach „ja“ fragen, laden, Hash prüfen.
4. **`messen.py`** mit echter Inferenz auf den Fixtures aus `benchmarks/fixtures.py` (und optional Tracks aus
   dem lokalen Manifest), nach dem Messplan im Bericht; ergänzen, wo es fehlt (DEMON, AFTER, Magenta,
   RoFormer/DrumSep). RTF je internem Block, wo das Modell blockweise arbeitet. Ergebnis über
   `benchmarks/spikes/runner.py` im Format aus Aufgabe 00.
5. Bericht des Kandidaten um die geschlossenen Punkte ergänzen.
6. `benchmarks/spikes/README.md`: Ablauf für den Koordinator je Kandidat als genau kopierbare Befehle.

## Nicht im Umfang

- Keine Messung, kein Gate (macht der Koordinator). Keine Gewichte im Repo.
- Kein Code unter `sirens/`, `web/`, `workers/`.

## Abnahme

1. Für mindestens RoFormer/DrumSep, SAM Audio und Stable Audio 3: Pins, `weights.json`, freigegebener
   `install.ps1` und `messen.py` mit echter Inferenz liegen vor.
2. Tests (ohne Netz, ohne GPU): `messen.py --dry-run` aller Kandidaten läuft; `weights.json` aller Kandidaten
   hat die Pflichtfelder; kein `install.ps1` lädt ohne `-ModelleLaden`; kein Messskript lädt Gewichte unsicher
   (Textprüfung auf `weights_only=False` und `pickle.load`).
3. CI des PR grün.
