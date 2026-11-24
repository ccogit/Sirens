# Aufgabe 19: Systemabnahme und Zuverlässigkeit (WP19)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP19“ und Kapitel 7 (Gate G4) in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 17 voraus.

## Ziel

Eine vollständige, wiederholbare Abnahme: CI ohne Modelle, eine Windows-Hardware-Suite für den Zielrechner, Soak-Skripte und ein Bericht je Funktion und Profil als Grundlage für Gate G4.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Alle Messskripte unter `benchmarks/`; Stand in `docs/realtime/board.md`.

## Umfang

1. Lücken in der CI schließen: Protokolltests mit erzeugtem Audio, Störfälle (GPU-Engpass, Speichermangel, Worker-Absturz, Verbindungsabbruch, Seek, Platte voll, ungültige Pfade, Origin, Token) je als Test mit Mock. Diese Aufgabe darf `.github/workflows/tests.yml` ändern.
2. `benchmarks/suite.ps1`: führt alle Messskripte der freigegebenen Funktionen nacheinander aus, sammelt Ergebnisse, prüft danach auf verwaiste Prozesse und unveränderte Originale (Hash).
3. Soak: 2 Stunden Performance-Profil, 30 Minuten je Streaming-Modell; Lookahead und Offline getrennt.
4. `docs/realtime/abnahme.md`: Matrix Funktion × Profil × Gate, Anleitung für Hörtests, Hintergrundtab, Gerätewechsel, Claude-Start, laufende Produktion.

## Nicht im Umfang

- Keine neuen Funktionen.
- Keine Gate-Entscheidung.

## Abnahme

1. Jeder Störfall aus Umfang 1 hat einen Test.
2. `benchmarks/suite.ps1 -DryRun` läuft ohne GPU durch und erzeugt einen Bericht mit `nicht_gemessen`.
3. Negativ: Ein verwaister Prozess oder eine veränderte Originaldatei lässt die Suite fehlschlagen (Test mit nachgestelltem Fall).
4. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft Gate G4: Soak und Hardware-Suite.
5. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
