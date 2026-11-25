# Ergebnis AUFGABE-35

- Die 48-kHz-Sperre im Live Lab entfällt; Mock-Sitzung und Serverquelle bleiben bei 48 kHz.
- Die Browserpumpe führt Quell-/Wire-Frames getrennt von Geräteframes. Transport und AudioCore nutzen pro Epoch den gleichen Ursprung; absolute ganzzahlige Framegrenzen (BigInt) erhalten den Rundungsrest ohne aufsummierten Fehler.
- Dry wird einmalig, Wet je Paket linear auf die Geräterate interpoliert. Gleiche Quellphase und Paketgrenzen; an den äußersten Interpolationssamples eines einzelnen Pakets werden Randwerte gehalten. Server und Vertragsdateien für Aufgabe 35 unverändert.

## Abnahme
1. `tests/realtime/pump_loop_34.test.mjs`: 100 Wechsel bei 44.100 Hz, 50 ms Produzentenlatenz; Soll: 0 unerwartete Underruns. In einer V8-Teilausführung mit aus GitHub gelesenen Originalfunktionen und simuliertem AudioWorklet/AudioCore bestanden. Nicht als vollständiger Node-Testlauf zu werten.
2. `tests/realtime/device_rate_35.test.mjs`: 345.600.000 Serverframes ergeben 317.520.000 Geräteframes; blockweise absolute Grenzen, exakte Rückumrechnung, Dry/Wet-Raster nach Seek. Beide Tests in derselben V8-Teilausführung bestanden.
3. Die vollständige Suite ist offen: Git-Checkout nicht möglich (DNS); laut KETTEN.md keine Actions-Läufe. Kein vollständiger Node- oder Python-Testlauf behauptet.
4. Diese Datei. Hörprüfung auf 44,1- und 48-kHz-Geräten nicht gemessen; Koordinator führt sie und G4 aus.

## Übergabe
Fertig: Implementierungen 37, 34, 35, Tests und Ergebnisdateien gepusht. Sechs gezielte JS-Prüfungen in V8 (zusammengeführte Originalmodule, DSP aus, minimale Assert-/Timer-Shims) bestanden: Seek-Bit, 100 Loopwechsel 48 kHz einschließlich Negativkontrolle, manueller Seek, 100 Loopwechsel 44,1 kHz, 2-h-Framegrenzen und Dry/Wet-Paketgrenzen. Keine Hardwaremessung.
Offen: reguläre Python-3.11-/Node-22-Gesamtsuite, reale Sidecar-/Browser-Last, G4-Soak, Hörprüfung. GitHub Actions laut Register deaktiviert; der Nutzerauftrag verlangt dennoch CI grün. Diese Abnahme kann deshalb hier nicht bestätigt werden.
Nächster Schritt: `py -3.11 -m unittest discover -s tests -v`, `node --test tests/realtime/pump_loop_34.test.mjs tests/realtime/device_rate_35.test.mjs tests/realtime/pcm_seek_37.test.mjs`; anschließend G4 wie in AUFGABE-34.md und Hörprüfung. Falls die CI wieder aktiviert wurde, den PR-Lauf prüfen.
Fehlerausgabe: `fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`.

Risiken: PCM-Minimum 256 Serverframes bei sehr kurzem Restloop, reale Timer-/IPC-Latenz, einzelne Randwerte bei Paketinterpolation. Keine zusätzlichen Abhängigkeiten oder fremden Pins/Lizenzen; Python 3.11, Node 22, CPU; Zielhardware nicht gemessen. Rückbau: AUFGABE-35-Commits revertieren, danach bei Bedarf 34 und 37.

## Nacharbeit zu PR #86 – Panic / Node-Gesamtlauf

Windows-Prüfung des Koordinators (vor dieser Nacharbeit): Python-Suite 259 Tests, nur `test_web` wegen 120-s-Timeout des Node-Gesamtlaufs fehlgeschlagen. `pcm_seek_37`, `device_rate_35`, `pump_loop_34`, `rt_contracts` und `loop_epoch_30` grün.

Ursache des Hängers in `integration_26.test.mjs`, Test „Panic während HTTP-Play startet keine lokale Audioausgabe“: Der gleichratige (48 kHz) injizierte AudioCore-Testadapter besitzt kein `configureSourceRate`. Der unbedingte Aufruf ließ die Initialisierung vor HTTP-Play mit TypeError abbrechen; das Test-Gate `waiting` wurde nie aufgelöst. Kein Warten auf loopPlan. Der unveränderte Testadapter braucht bei 48 kHz keine Ratenkonfiguration; für andere Raten bleibt sie zwingend.

Zusätzlich in shell.js: Panic/Verlassen invalidiert den Renderplan und löscht das Pumpintervall synchron. Timer-Callbacks und asynchrone Initialisierung sind an die Sitzungsgeneration gebunden. Der ausstehende Pump-Promise wird bei Cleanup abgewickelt, bevor die Ressourcen geschlossen werden; nach Invalidierung keine weiteren Renderaufträge oder veralteten Status-/Fallback-Updates. Ein bereits gesendeter HTTP-Renderauftrag wird nicht abgebrochen, sondern bis zu seiner Antwort bzw. zum bestehenden 15-s-HTTP-Timeout abgewickelt. Ein automatisch vorgemerkter Pause-Befehl prüft ebenfalls die Sitzungsgeneration.

Der bestehende Regressionstest wurde nicht geändert. Neue Tests in `tests/realtime/pump_lifecycle_35.test.mjs`: reset und destroy während eines ausstehenden Renderauftrags, sofortige Intervalllöschung, keine weiteren Aufträge auch bei nachlaufendem Timer-Callback, keine verspätete Fehler-/Statusmeldung, genau einmaliges Schließen und Zerstören der Ressourcen.

Prüfbeleg nach der Korrektur: fünf gezielte V8-Teilprüfungen mit Originalfunktionen aus shell.js, transport.js, mock_api.js und api.js, Timer-/Assert-Shims: drei unveränderte Sitzungs-/Panic-Tests aus integration_26 (einschließlich des gemeldeten Hängers) und beide neuen Lebenszyklustests bestanden; jeweils keine offenen Testtimer. Regulärer Node-22-Lauf nach dem Fix nicht möglich: Git-Zugriff erneut `Could not resolve host: github.com`. Keine grüne Gesamtsuite behauptet.

Nächster Prüfschritt beim Koordinator: `node --test tests/realtime/integration_26.test.mjs tests/realtime/pump_lifecycle_35.test.mjs`, anschließend `py -3.11 -m unittest discover -s tests -v` und G4/Hörprüfung wie oben. Der PR wird nach Anforderung des Koordinators ohne ÜBERGABE-Präfix wieder zur Prüfung bereitgestellt.
