# Lokaler Qualitätsbenchmark K06

Nur lokale, nicht eingecheckte Run-Verzeichnisse und Manifeste verwenden. Keine Downloads.
Ein Manifest neben den Runs, z.B. `{"schema_version":1,"runs":["run-1","run-2"]}` (relative Pfade).
Aufruf:

```
python -m sirens.production.quality --manifest /lokal/benchmark.json --output /lokal/report.json
```

Optional mit dem bereits eingerichteten isolierten Python-Worker und vorhandenem Checkout der Mastering-Engine:
```
python -m sirens.production.quality --manifest /lokal/benchmark.json --analysis-python /lokal/worker/bin/python --analysis-root /lokal/engine
```

JSON: schema_version, runs[] mit technical, music, production, gates, missing, provenance, listening, next_improvements. Exit 1 bei technischen Fehlern. Ausgabedatei wird nicht überschrieben. Sample-Peak ist kein True-Peak. Fehlende Messungen bleiben null.

Blindprotokoll B1/B2 (noch manuell zu orchestrieren): `allocate_pair` mit gemessener LUFS und eindeutigem pair_id, brief_id, repetition aufrufen; Mapping nur lokal beim Operator halten. A/B-Dateien separat nach den berechneten gain_db-Werten absenken, Originalmaster unangetastet halten, erneut messen (max. 0,5 LU Unterschied), keine Modell-/Dateinamen zeigen. Präferenz verdeckt als A/B/tie festhalten und sperren; danach ausschließlich neuen Kandidaten auf Musik/Produktion 1–5 bewerten (keine neuen Referenzbewertungen). `reveal_pair` prüft Lock, Paar-ID, Lautheitsabstand und Skalen; `summarize_b2` prüft die numerische Mindestschwelle, erteilt ausdrücklich keine Freigabe. B1: drei 30–60 s Kandidaten je Brief; B2: drei Vollsong-Briefs, zwei Kandidaten je Brief, zwei zeitlich getrennte Wiederholungen. Reale Messung und Hörurteile nicht gemessen; Abspielkopien, persistenter Vote-Lock und WB-Speicheranbindung offen. Kein Qualitätsnachweis aus Mock-Tests.
