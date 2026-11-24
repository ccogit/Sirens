# Aufgabe 20: Rollout, Installation, Runbook (WP20)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP20“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 19, das bestandene Gate G4 und die Freigabe des Repo-Eigentümers voraus.

## Ziel

Ein nachvollziehbarer Weg zur Installation und zurück: Skripte je Worker, Diagnose, Lizenzmatrix, Handbuch mit den tatsächlich gemessenen Modi und Latenzen, Release Candidate.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Installationsskripte der Worker unter `workers/*/install.ps1`; Messergebnisse unter `benchmarks/results/`; bestehende Anleitung `docs/stem-studio.md`; `start.ps1`.

## Umfang

1. `scripts/rt-install.ps1`: Auswahl je Worker, feste Versionen und Hashes, Diagnose von Treiber und CUDA, Prüfung von Plattenplatz und VRAM, Modell-Download nur mit Zustimmung, kein globales Python, Deinstallation, Rückfall über `SIRENS_RT_ENABLED`.
2. `docs/realtime/`: Installationsanleitung, Lizenzmatrix, Fehlersuche, Nutzerhandbuch mit gemessenen Modi und Latenzen (aus `benchmarks/results/`, nichts Geschätztes), Runbook.
3. Changelog und Vorschlag für den Tag des Release Candidate im PR-Text. Diese Aufgabe darf `README.md` und `.env.example` ändern.

## Nicht im Umfang

- Kein Tag, kein Release, kein Merge nach `main`: Das macht der Repo-Eigentümer.

## Abnahme

1. Tests: `scripts/rt-install.ps1 -DryRun` zeigt alle Schritte ohne Änderung; kein Download ohne Schalter (Textprüfung); Deinstallation entfernt nur eigene Ordner.
2. Test: Mit Schalter aus und ohne installierte Worker läuft der Bestand unverändert.
3. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: frische Installation am Zielrechner.
4. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
