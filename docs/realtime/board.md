# WP-Board

Anfangsstand gemäß AUFGABE-00. A0 pflegt den Stand beim Merge oder Capability-Wechsel. Dieses Board ersetzt nicht das Kettenregister. Zulässige Status: `queued`, `in_progress`, `blocked`, `review`, `done`, `deferred`. Einträge ohne Beleg bleiben offen; `review` ist der geforderte Vorlagenstatus, keine Aussage über eine bereits grüne CI.

| wp | owner | depends_on | branch | commit | tests | gate | blockers | next_action | status |
|---|---|---|---|---|---|---|---|---|---|
| WP00 | KETTE-00 | – | extern/KETTE-00 | b2be62ec | CI: 91 Tests, 4 bestehende Skips | nicht_gemessen | Zielrechner nicht gemessen | A0: Review und Baseline | review |
| WP01 | KETTE-11 | 00 | extern/KETTE-11 | da8f1362 | PR #8, CI ausstehend | nicht_gemessen | Alt-DSP-Ausnahme siehe Ergebnis | A0: Review der v1-Verträge | review |
| WP02 | – | 00 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP03 | – | 01 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP04 | – | 01 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP05 | – | 01 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP06 | – | 03, 04, 05 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP07 | – | 02 (G1 DEMON), 06 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP08 | – | 02 (G1 Separation), 03 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP09 | – | 02, 04 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP10 | – | 01 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP11 | – | 02 (G1 RAVE/AFTER), 06 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP12 | – | 02 (G1 Stable Audio), 06, 10 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP13 | – | 02 (G1 SAM Audio), 03 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP14 | – | 06, 08, 09, 10 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP15 | – | 02 (G1 Magenta), 06, 10 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP16 | – | 04, 06 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP17 | – | 08, 09, 14, 16 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP18 | – | 10, 14, 16; neuronaler Pfad freigegeben | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP19 | – | 17 | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
| WP20 | – | 19; G4 bestanden; Freigabe | – | – | – | nicht_gemessen | – | Zuweisung durch A0 | queued |
