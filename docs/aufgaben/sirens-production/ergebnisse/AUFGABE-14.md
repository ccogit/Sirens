# AUFGABE-14 – Inventur mit AMM-Export

CLI inventory liest die Einstellungen einmal via integration.settings() und lädt amm_export über read_manifest; Übergabe an collect. references verwendet den bereits implementierten integration.references-Adapter ausdrücklich mit denselben Einstellungen. Ohne Export bleibt missing_sources erhalten.

Abnahme: tests/production/test_cli_amm_export.py erzeugt temporäre Konfiguration, Export, WAV und Brief. Beide CLI-Aktionen müssen with_prompts=1 liefern und amm_export darf nicht in missing_sources stehen. Keine echten Daten. Reuse: P08 integration.settings/references und K01 collect (REUSE).

Aufruf: SIRENS_PRODUCTION_CONFIG auf lokale JSON-Datei mit schema_version=1 und amm_export (lokaler Dateipfad) setzen; py -3.11 -m sirens.production inventory bzw. references --brief <datei>.

Tests geschrieben, nicht ausgeführt: kein vollständiger Checkout in dieser Sitzung. Windows-Prüfung beim Koordinator, Actions abgeschaltet. Reale Inventurzahlen nicht gemessen. Keine Änderungen an integration.py oder Konfigurationsschema.
