# AUFGABE-32 – G4-Mess-Harness (KETTE-55)

Voraussetzungen: WP04, WP16, WP19 gemergt. Änderungen nur in den zugewiesenen Benchmark-Dateien, an der Cache-Suche und in eigenen Tests. Integrationsstand fd5489d9 in 4ee27ca5 gemergt, ohne eigene Registeränderung.

## Umsetzung und Abnahme

| Punkt | Umsetzung und Test in tests/realtime/test_g4_harness.py |
|---|---|
| 1 | Beide lokalen HTTP-Server liefern JS-Module inkl. Unterordnern; Host, Pfadsegmente, aufgelöster Dateipfad und Dateityp werden geprüft. test_module_servers prüft rack.js, spectral.js, direkte Module, Traversal, absolute URL und fremden Host über lokale HTTP-Verbindungen. Recorder-POST unverändert. |
| 2 | Prozessinventar: explizit UTF-8, JSON und Struktur validiert, fünf Versuche mit 0,5 s Pause. Dauerausfall markiert den betroffenen Pfad als Fehler, beendet den laufenden Unterprozess; nächste Pfade laufen weiter. test_snapshot_retry (kaputtes JSON, Timeout, Erholung, Dauerausfall) und test_snapshot_failure_isolated (erster Pfad Fehler, zweiter erfolgreich). |
| 3 | Vorprüfung des relativen Separation-WAV unter --music-root vor Prozessstart; Meldung mit Soll/Ist (44100 Hz, 2 Kanäle). test_separation_preflight: 48 kHz Stereo, 44,1 kHz Mono, gültige Stereo-Datei. |
| 4 | Cache-Override hat Vorrang, sonst Suche in Manifest-python_dirs/weights nach gepinnter Revision. Hashprüfung unverändert. test_cache_search_and_override ohne echte Gewichte. |
| 5 | Neue CPU-/Mock-Tests geliefert; vollständiger Testlauf offen. |

Alle genannten Tests implementiert, nicht ausgeführt. Hardware, Browser/Ton, G4: **nicht gemessen**. Kein neues Gate-Ergebnis.

## Nachstellen

Windows: `py -3.11 -m unittest discover -s tests -p test_g4_harness.py -v`, danach `py -3.11 -m unittest discover -s tests -v` (Node 22). Unter Linux entsprechend python3.11.
Danach benchmarks/suite.ps1 -DryRun und Hardwarelauf mit -MusicRoot, -Plan und -OutputDir gemäß WP19; Ausgabe suite.json im externen Ordner.

## Grenzen und Risiken

Keine neuen Fremdprojekte, Pins oder Lizenzen. Stable-Audio-Revision 8bdfb53c6b0fbc62113cd571fd37373efe15fa14 und Stability AI Community License unverändert. Keine Downloads, Gewichte oder Kundendaten. Zielhardware Windows 11 / RTX 5080. MusicRoot muss dem Musikordner des Dienstes entsprechen. Vorprüfung erkennt den product_job aus dem Beispielplan; andere Separation-Aufrufe werden abgewiesen. Keine neue feste Eingaberate für synthetische oder resamplende Messpfade. Interaktive Browser-/Hörschritte aus WP19 bleiben erhalten; keine Browserautomatisierung. Inventar stichprobenbasiert; Dauerfehler können die Nachkontrolle beeinträchtigen. Fünf Timeouts können bis zu fünf Minuten dauern.

Rückbau: eigene AUFGABE-32-Änderungscommits revertieren, Integrationsmerge nicht revertieren.

## Übergabe

Fertig: fünf konkrete Harnessprobleme bearbeitet, Tests und Ergebnisdatei gepusht. Offen: Testausführung und Windows-G4-Lauf. Nächster Schritt: obige Befehle durch Koordinator ausführen. Fehlerausgabe: lokaler Git-Zugriff `Could not resolve host: github.com`; Actions abgeschaltet. Frühe GitHub-Schreib-/GraphQL-Fehler (ReadTimeout) durch Wiederholung bzw. direkte Serveranpassungen überwunden. PR #79 ist auf Ready for review gesetzt.
