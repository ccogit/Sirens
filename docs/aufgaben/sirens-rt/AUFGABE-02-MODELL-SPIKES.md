# Aufgabe 02: Modell-Spikes – Berichte und Messskripte (WP02)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP02“,
Kapitel 7 (Gate G1) und Kapitel 9 (Kandidaten) in `docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 00 voraus.

## Ziel

Für jeden Modellkandidaten soll der Koordinator auf dem Zielrechner mit einem einzigen dokumentierten Ablauf
messen können, ob und in welchem Modus das Modell taugt (Gate G1: grün, amber, rot). Diese Aufgabe liefert je
Kandidat einen geprüften Machbarkeitsbericht aus den Quellen und ein fertiges, abgeschottetes Messskript. Die
Messung selbst und damit die Gate-Entscheidung gehören nicht dazu.

## Ausgangslage

- Der Bearbeiter hat keine RTX 5080. Jede Leistungszahl aus fremden Quellen ist eine Angabe Dritter, kein
  Ergebnis.
- Aus Aufgabe 00: `benchmarks/fixtures.py` (Testsignale), `benchmarks/result.py` und
  `benchmarks/result.schema.json` (Ergebnisformat), `benchmarks/baseline.py`, lokales Track-Manifest.
- `docs/stem-studio.md` zeigt, wie Sirens heute eine getrennte Umgebung für Demucs einrichtet
  (`.venv-stems`, PyTorch mit CUDA-Index).
- Kandidaten (Links in `PLAN.md`, Kapitel 9): DEMON, Stable Audio 3, Magenta RealTime, RAVE, AFTER,
  RoFormer/DrumSep (Music-Source-Separation-Training, pymss), SAM Audio, GPU Audio SDK, Beat This! Live,
  Signalsmith Stretch.

## Umfang

Je Kandidat ein Ordner `benchmarks/spikes/<kandidat>/` mit:

1. **`BERICHT.md`**: Was das Projekt tatsächlich kann (aus Repository und Dokumentation, mit Fundstelle);
   geprüfter Commit oder Version; Lizenz des Codes und – getrennt – der Gewichte, mit Folgen für lokale
   Nutzung und Weitergabe; Bezugsquelle und Größe der Gewichte; Betriebssysteme (Windows nativ, WSL2);
   Anforderungen an Python, CUDA, PyTorch, TensorRT; Unterstützung der RTX-50-Reihe (Blackwell, `sm_120`),
   soweit belegt; tatsächlicher Betriebsmodus nach Quellenlage (`streaming`, `lookahead`, `offline`) mit
   Kontext-, Hop- und Latenzangaben; steuerbare Parameter; VRAM-Angaben Dritter (als solche gekennzeichnet);
   Risiken; Empfehlung, was zu messen ist und welche kleinere Variante als Ausweichweg dient. Ist ein Link
   tot oder ein Projekt nicht auffindbar: genau das festhalten, nichts ersetzen oder erfinden.
2. **`install.ps1`**: legt eine eigene, wegwerfbare Umgebung an (`.venv-spike-<kandidat>` im Repo-Ordner,
   passt auf `.venv*/` in `.gitignore`), mit festen Versionen. Lädt nichts ohne den Schalter
   `-ModelleLaden`; zeigt vorher Quelle, Größe und Lizenz und fragt nach. Verändert kein globales Python und
   nichts an der produktiven Sirens-Umgebung. Parameter `-Entfernen` baut alles zurück.
3. **`messen.py`**: läuft in dieser Umgebung, nimmt Testsignale aus `benchmarks/fixtures.py` und optional
   Tracks aus dem lokalen Manifest, führt **echte Inferenz** aus (nicht nur Import) und schreibt ein Ergebnis
   im Format aus Aufgabe 00 nach `benchmarks/results/local/`: kalt und warm, Zeit bis zum ersten Ergebnis,
   RTF je Block mit p50/p95/p99, Peak-VRAM (Prozess und ganze GPU), CPU gegen GPU, bei Streaming ein
   10-Minuten-Lauf, bei Generierung mehrere Seeds; schreibt Hörproben nach `benchmarks/results/local/`.
   Bricht mit klarer Meldung ab, wenn Umgebung oder Gewichte fehlen. Parameter `--dry-run` prüft nur Aufbau
   und Argumente ohne Modell.
4. **Übersicht** `benchmarks/spikes/README.md`: Tabelle aller Kandidaten mit Lizenzampel, vermutetem Modus,
   Reihenfolge der Messung (was die Ketten 26, 27, 33 bis 36 freischaltet) und dem Ablauf für den
   Koordinator in nummerierten Schritten. Spalte „Gate“ überall `nicht_gemessen`.
5. **Gemeinsame Messhilfe** `benchmarks/spikes/common.py` (Zeitmessung, Perzentile, VRAM über `nvidia-smi`
   oder `torch.cuda`, Ergebnis schreiben), mit Tests.
6. Für GPU Audio SDK, Signalsmith Stretch und Beat This! Live genügt statt `messen.py` ein Bericht mit
   Integrationsweg (Sprache, Build, Bindung an Browser oder Worker) und ein Messplan, wenn ein Python-Skript
   nicht passt.
7. `docs/realtime/board.md` fortschreiben (WP02: je Kandidat eine Zeile, Gate `nicht_gemessen`).

## Nicht im Umfang

- Keine Gate-Entscheidung, keine Zahl als eigenes Messergebnis.
- Kein Code unter `sirens/`, `web/` oder `workers/`. Kein Adapter (das sind die Aufgaben 07 bis 15).
- Keine Gewichte, keine fremden Quelltexte im Repo; nur Verweise mit Commit oder Version.
- Fremden Code nicht ungeprüft empfehlen: Wo ein Installationsweg fremde Skripte ausführt, steht das im
  Bericht.

## Abnahme

1. Für jeden der zehn Kandidaten gibt es `BERICHT.md` mit allen Punkten aus Umfang 1; jede Aussage zu
   Lizenz, Modus und Anforderungen hat eine Fundstelle (Datei oder Abschnitt im Projekt-Repository, mit
   Commit oder Datum des Abrufs).
2. Tests (ohne Netz, ohne GPU): `benchmarks/spikes/common.py` rechnet Perzentile und RTF richtig; jedes
   `messen.py` läuft mit `--dry-run` fehlerfrei und meldet ohne Umgebung verständlich, was fehlt; ein mit der
   Messhilfe erzeugtes Beispielergebnis besteht `benchmarks/result.schema.json`.
3. Test: Kein `install.ps1` enthält einen Download ohne den Schalter `-ModelleLaden` (Prüfung über den
   Text) und keines ruft `pip install` ohne `--prefix` oder aktivierte eigene Umgebung auf.
4. In keiner Datei steht ein Gate außer `nicht_gemessen`; Zahlen aus fremden Quellen sind als solche
   gekennzeichnet.
5. `python -m unittest discover -s tests -v` läuft durch.
