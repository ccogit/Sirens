# AUFGABE-13 – AMM-Export

Implementiert: lokaler JSONL-Adapter (Standardbibliothek), bestehendes parse_pfad, safe_path und Exportprojektion aus K01 wiederverwendet. Kein DB-Zugriff, kein SQL, keine Netzwerkzugriffe. Die optionale DB-Befehlsanbindung wird nicht angeboten; die lesende Zeilenextraktion bleibt beim AMM-Owner.

Aufruf (Dateien außerhalb des Checkouts):
```
py -3.11 -m sirens.production.references amm-export --input <lokale-zeilen.jsonl> --out <lokaler-export.json>
```
SIRENS_MUSIC_ROOT auf den lokalen Katalog setzen. Eine JSON-Zeile pro Job/Paket: local_file_path, package_created_at (ISO-8601), package_id (numerisch, Tie-Break), song_id, style_prompt, negative_tags, lyrics, parameters, axes, song_evaluations (Liste mit id, outcome_score, favorite, comment, axes). Pfade relativ zum Musikordner; .\\generated-music\\ wird entfernt. Fehlende oder unsichere Dateien werden ausgelassen. Ausgabe: schema_version=1, songs; stdout nur Anzahl. Keine privaten Inhalte im Repo. Bewertungen tragen scope=song und eine stabile evaluation_id; in der Inventur werden Rohurteile und Kommentare über Fassungen dedupliziert.

| Abnahme | Beleg |
|---|---|
| Dubletten, neuestes Paket | test_projection_and_inventory |
| Windows-Präfix, fehlende Dateien und Traversal | gleicher Test |
| Song-Bewertung über zwei Versionen | gleicher Test, raw_ratings=1, comments=1 |

Reuse: Sirens K01 Exportindex/collect und parse_pfad (ADAPT), kein neuer Katalog; AMM @ 26c5ce2fe9641ed958414f78d58643527bc3032f dokumentierter lesender Lookup, lokale Zeilenprojektion (ADAPT). Reale AMM-Abfrage und Zeitstempel-/ID-Feldzuordnung nicht geprüft. Die tatsächliche lokale Zeilenerzeugung ist vom Koordinator zu bestätigen. Keine neue Abhängigkeit.

Tests bereitgestellt, nicht lokal ausgeführt: vollständiger Checkout in dieser Sitzung nicht vorhanden. Actions deaktiviert, Windows-Prüfung offen.
