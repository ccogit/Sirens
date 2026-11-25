# AUFGABE-32 – G4-Mess-Harness

WP04, WP16, WP19 vorausgesetzt. Beide lokalen HTTP-Server erlauben verschachtelte Realtime-JS-Module mit Host- und Pfadprüfung. Prozessinventar: UTF-8, fünf Versuche, Fehlerisolierung. Separation: 44100 Hz Stereo vorprüfen. Stable Audio: Cache-Suche über Manifest, Env-Vorrang, Hashprüfung unverändert.

## Abnahme

Tests in tests/realtime/test_g4_harness.py: test_module_servers (Rack, Unterordner, Traversal, fremder Host), test_snapshot_retry und test_snapshot_failure_isolated, test_separation_preflight (48 kHz, Mono, gültiges Stereo), test_cache_search_and_override. Nicht ausgeführt: lokaler Git-Zugriff meldet Could not resolve host: github.com. Actions abgeschaltet. Hardware/G4 nicht gemessen.

## Übergabe

Fertig: Code und Tests gepusht. Offen: Windows-Abnahme mit `py -3.11 -m unittest discover -s tests -v` (Node 22), danach benchmarks/suite.ps1 gemäß WP19. Linux: python3.11. MusicRoot muss dem Dienst entsprechen; interaktive Browser-/Hörschritte bleiben. Keine neuen Abhängigkeiten, Pins oder Lizenzen. Rückbau: eigene AUFGABE-32-Commits revertieren. Ready-for-review-Versuche meldeten ReadTimeout und GraphQL-Fehler; Koordinator prüft PR-Status.
