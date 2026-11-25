# AUFGABE-15 – Benchmark-Messung

Die Produktions-CLI liest analysis_python und analysis_root aus der vertrauenswürdigen lokalen Konfiguration und reicht configured_analyzer an benchmark weiter. Vorrang: vorhandener mastering_engine im isolierten Worker (REUSE, AMM @ 26c5ce2fe9641ed958414f78d58643527bc3032f, bestehender K06-Adapter). Rückfall bei fehlender oder nicht auflösbarer Worker-Konfiguration: lokales ffmpeg (konfigurierter Pfad oder PATH), ebur128=peak=true (ADAPT). Keine Modellimporte, keine neuen Bibliotheken. True Peak aus dem True-peak-Abschnitt, nicht aus PCM-Sample-Peak. Fehlt eine Messung oder scheitert der Analyzer beim Aufruf, bleiben Werte null und der Bericht nennt den Grund; keine erfundenen Werte. Ein zur Laufzeit scheiternder konfigurierter Worker wird nicht automatisch erneut über ffmpeg ausgeführt.

Abnahme / Tests: tests/production/test_quality_analyzer.py:
- test_cli_configured_worker: Konfiguration in temporärer Datei, Worker-Factory und Benchmark gemockt, Übergabe des Analyzers geprüft.
- test_ffmpeg_summary: synthetische FFmpeg-Ausgabe, LUFS, dBTP und LRA sowie UTF-8-Subprocess-Aufruf geprüft.
- test_missing_analyzer_and_mock_metrics: ohne Analyzer null + Grund, mit Mock Analyzer Messwerte und Methode.

Aufruf: py -3.11 -m sirens.production benchmark --manifest <lokales-benchmark-manifest.json>. Erwartet: runs[].technical.mix/master mit lufs, true_peak_dbtp, measurement_method bzw. measurement_reason. Standalone quality-CLI kann ebenfalls ffmpeg als Rückfall verwenden. Reale LUFS/True-Peak-Werte nicht gemessen.

Lokaler Checkout nicht möglich: git ls-remote https://github.com/ccogit/Sirens.git refs/heads/extern/KETTE-P12 -> fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com. Code und Tests über GitHub-API geschrieben. Keine lokale Testausführung; Actions abgeschaltet. Koordinator: py -3.11 -m unittest discover -s tests -v und realer Benchmark auf Zielrechner. Risiken: tatsächliche FFmpeg-Ausgabeversion, lokale Worker-/Dateipfade und Windows-Abnahme offen; keine Aussage zur Hörqualität.
