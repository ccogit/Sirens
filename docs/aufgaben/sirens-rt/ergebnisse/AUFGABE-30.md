# AUFGABE-30 – Teilstand

Worklet: zwei Wet-Ringe, Wechsel am Loop-Frame ohne Mix-/DSP-Reset, kumulative getrennte Seek-/Loop-Underruns. AudioCore: loopPlan mit Epoch, Frame, Quelle und Vorlauf; getrennte Transport-Credits und Sequenzen.

## Abnahme
1. tests/realtime/loop_epoch_30.test.mjs: RenderPath mit 100 Wechseln und Negativkontrolle, Ausfallmodell der alten Generation (2400 Frames); vollständige Produzenten-/Worklet-Taktsimulation offen. Nicht ausgeführt.
2. Seek-Lücke/alte Epoch/unerwartete Folgelücke im selben Test, nicht ausgeführt.
3. 44100 Hz offen: shell.js sperrt Geräte mit anderer Rate; sessions.py und mock.py erwarten 48000 Hz. Dateien außerhalb der Kette.
4. Vollsuite nicht geprüft: Clone fehlgeschlagen (Could not resolve host: github.com); CI aus. Windows: py -3.11 -m unittest discover -s tests -v; node --test tests/realtime/loop_epoch_30.test.mjs.
5. G4 nicht gemessen; Soak/Report-Trennung noch offen. Nach Einbau: Performance, synthetisches Testsignal, 100 % Wet, 4-s-Loop, benchmarks/g4/soak.js in DevTools, 7200 s; py -3.11 -m benchmarks.g4.report <Rohdatei> --candidate Performance --out <Ergebnisdatei>.

## Übergabe
Fertig: Worklet-/AudioCore-Grundlage und RenderPath-Regression. Offen: tatsächliche Produzentenplanung, 44,1 kHz, G4-Auswertung, vollständiger Test. Nächster Schritt: Koordinator integriert shell.js/pump (aktuelle Generation bis Ende vorfüllen, loopPlan rechtzeitig nutzen, neue Sequenz ab 0, Quelle/Frame aus Plan), sessions.py/Session.render und Worker-Schleife (alte und nächste Audio-Epoch getrennt zulassen, nicht beim Annehmen der neuen alle alten Jobs verwerfen), Seek-Flag durchreichen. Beide Dateien sind nicht zur Änderung freigegeben. 48-kHz-Serverquelle beibehalten und Framekoordinaten sowie Dry/Wet für Gerätesamplerate umrechnen. Keine neuen Abhängigkeiten/Modelle/Pins. Risiken: kurze Loops, verspätete Pakete, DSP-Verhalten, noch keine Hörprüfung. Rollback: Ketten-Commits revertieren.

Fehler: Clone DNS; GitHub Contents API 409 "Timed out validating the rule" (AudioCore-Wiederholung erfolgreich), ReadTimeout bei größerem Test (kleiner Test erfolgreich), interner Toolfehler bei Soak-/Dokumentationsschreibversuch. Keine Register- oder Boardänderung.
