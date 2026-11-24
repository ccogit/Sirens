# Aufgabe 00: Baseline und Testgerüst (WP00)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP00“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt nichts voraus.

## Ziel

Alle folgenden Aufgaben brauchen dasselbe Gerüst: einen Ort für Echtzeit-Tests, erzeugbare Testsignale, ein
festes Format für Messergebnisse, eine ADR-Vorlage und ein Skript, das den Zielrechner beschreibt. Diese
Aufgabe legt das an, ohne das Verhalten von Sirens zu ändern.

## Ausgangslage

- Der Integrationszweig `integration/sirens-rt` existiert schon (vom Koordinator angelegt). Die beiden
  aufgehobenen Prüfungen (400 Zeilen, externe Frontend-Quellen) sind dort bereits aus `tests/test_web.py`
  entfernt, die Content-Security-Policy in `sirens/server.py` lässt `https:` zu. Daran nichts ändern.
- `tests/test_web.py`, Test `test_logik_mit_node`: ruft `node --test` mit zwei fest genannten Dateien auf
  (`tests/logic.test.mjs`, `tests/stem_visual.test.mjs`).
- `tests/hilfe.py`: gemeinsame Testhilfen (temporäre Ordner, nachgebauter Musikordner, HTTP-Aufrufe).
- Die CI (`.github/workflows/tests.yml`) führt nur `python -m unittest discover -s tests -v` aus.
- `sirens/beat.py` liest Audio über `ffmpeg`; WAV-Dateien lassen sich mit dem Modul `wave` der
  Standardbibliothek schreiben.

## Umfang

1. **Node-Tests rekursiv.** `tests/test_web.py`: `test_logik_mit_node` sammelt alle `*.test.mjs` unter
   `tests/` rekursiv ein (sortiert), statt zwei Dateien fest zu nennen. Ein Fehlschlag nennt die Ausgabe von
   Node. `test_javascript_module_syntax` prüft `web/js/` rekursiv (auch `web/js/realtime/`).
2. **Ort für Echtzeit-Tests.** `tests/realtime/__init__.py` und ein erster Test `tests/realtime/test_fixtures.py`
   (siehe 3), der von `python -m unittest discover -s tests` gefunden wird.
3. **Erzeugbare Testsignale.** `benchmarks/fixtures.py` (nur Standardbibliothek), als Modul und als Befehl
   `python -m benchmarks.fixtures --out <ordner>`: Impuls, Sinus 440 Hz und 1 kHz, Stereo-Sinus mit
   verschiedenen Frequenzen je Kanal, Klickspur mit 120, 140 und 150 BPM (je mit betontem Taktanfang im
   4/4-Takt), Stille. Parameter: Abtastrate (Vorgabe 48000), Dauer, Kanäle. Ausgabe als WAV 32-bit float
   oder 24-bit PCM und als Liste von Abtastwerten für Tests. Deterministisch: gleicher Aufruf, gleiche
   Bytes. Jedes Signal bringt seine Wahrheit mit (z. B. Schlagzeiten in Frames).
4. **Manifest für lokale Testtracks.** `benchmarks/tracks.example.json` und `docs/realtime/testdaten.md`:
   Format eines lokalen Manifests `benchmarks/tracks.local.json` (Pfad, SHA-256, Genre aus Techno, House,
   Psytrance, Industrial, Ambient, Lizenzhinweis, optionale BPM-Referenz). `benchmarks/manifest.py` prüft ein
   Manifest (Datei vorhanden, Hash stimmt) und kann Hashes eintragen. `benchmarks/tracks.local.json` und
   `benchmarks/results/local/` stehen in `.gitignore`. Keine Musikdatei im Repo.
5. **Format für Messergebnisse.** `benchmarks/result.schema.json` und `benchmarks/result.py`: ein Ergebnis hat
   mindestens `wp`, `kandidat`, `gate` (`green|amber|red|nicht_gemessen`), `modus`
   (`streaming|lookahead|offline|unbekannt`), Zeitpunkt, Rechnerbeschreibung (aus 6), Messwerte mit
   p50/p95/p99, warm/kalt, Peak-VRAM, RTF, Underruns, Notizen, Befehl zum Nachstellen. `result.py` schreibt
   und prüft solche Dateien ohne fremde Bibliothek (eigene, kleine Schemaprüfung genügt) und erzeugt daraus
   einen Markdown-Bericht.
6. **Baseline-Skript.** `benchmarks/baseline.py`, Aufruf `python -m benchmarks.baseline --out <datei.json>`:
   erfasst Betriebssystem, Python, Node, ffmpeg, `nvidia-smi` (Treiber, GPU-Name, VRAM gesamt und frei),
   WSL vorhanden, freien Plattenplatz des Repo-Laufwerks, `git`-Stand (SHA, sauber oder nicht). Jedes
   fehlende Werkzeug ergibt `null` und einen Hinweis, keinen Abbruch. Keine Benutzernamen, keine Pfade aus
   dem Benutzerordner in der Ausgabe (kürzen auf Laufwerk und letzte Komponente).
7. **Vorlagen.** `docs/realtime/adr/0000-vorlage.md` (Titel, Status, Kontext, Entscheidung, Folgen,
   Alternativen), `docs/realtime/board.md` (Tabelle aller WP mit den Feldern aus `PLAN.md`, Kapitel 8:
   `wp`, `owner`, `depends_on`, `branch`, `commit`, `tests`, `gate`, `blockers`, `next_action`, Status
   `queued|in_progress|blocked|review|done|deferred`; Anfangsstand: alles `queued`, WP00 `review`),
   `docs/realtime/baseline.md` (wie der Koordinator Baseline und Fixtures erzeugt).
8. `benchmarks/__init__.py` anlegen; `benchmarks/README.md` mit den Befehlen.

## Nicht im Umfang

- Kein Code unter `sirens/` oder `web/`. Keine Änderung an `.github/workflows/tests.yml`.
- Keine Verträge, keine Architektur (Aufgabe 01), keine Modellprüfung (Aufgabe 02).
- Die Baseline des Zielrechners selbst: Die erzeugt der Koordinator mit dem Skript.

## Abnahme

1. `python -m unittest discover -s tests -v` läuft durch; die Zahl der bisherigen Tests ist nicht kleiner
   geworden, die Tests unter `tests/realtime/` laufen mit.
2. Test: Eine neue Datei `tests/realtime/beispiel.test.mjs` wird von `test_logik_mit_node` ohne Eintrag in
   einer Liste ausgeführt (mit einem echten kleinen Test belegen, der im Repo bleibt).
3. Tests zu den Fixtures: gleiche Parameter ergeben gleiche Bytes; die Klickspur mit 120 BPM hat bei 48 kHz
   ihre Schläge genau alle 24000 Frames; Impuls hat genau einen Wert ungleich null; WAV-Kopf stimmt
   (Rate, Kanäle, Länge); kein Wert über 1,0.
4. Tests zum Ergebnisformat: gültiges Beispiel wird angenommen; fehlendes Pflichtfeld und unbekannter
   Gate-Wert werden mit verständlicher Meldung abgelehnt.
5. Tests zum Manifest: fehlende Datei und falscher Hash werden gemeldet (temporäre Dateien).
6. Test zur Baseline: läuft ohne `nvidia-smi` und ohne `ffmpeg` (Aufrufe ersetzt) ohne Fehler und liefert
   `null` für die fehlenden Angaben; die Ausgabe enthält keinen Benutzerordner.
7. Negativ: Kein Test braucht Netz, GPU oder eine Musikdatei.
