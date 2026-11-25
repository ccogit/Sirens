# Ergebnis AUFGABE-34

- Browser-Pumpe nutzt loopPlan für die nächste Rendergeneration mit eigener Seq, Quelle und Ausgabeframe. Der erste Block wird bei Puffergröße plus Renderlatenz vorgezogen; weitere Blöcke bleiben im gemeinsamen zeitlichen Vorlauf. Die alte Generation wird bis zum Ende gerendert, die vorbereitete bei Epochwechsel übernommen.
- AudioCore misst vom Auftrag bis zum angenommenen PCM-Block in Geräteframes; konservativer Mindestvorlauf 50 ms. Manueller Seek setzt expectedSeek im Worklet und seek im ersten Renderauftrag; auch bei Play nach pausiertem Seek.
- HTTP-503/stale_epoch: Auftrag nicht als erfolgreich fortschreiben.

## Abnahme (Testcode vorhanden, Ausführung offen)
1. `node --test tests/realtime/pump_loop_34.test.mjs`: echter AudioCore und Worklet mit simuliertem 50-ms-Produzenten, 100 Wechsel, 0 unerwartete Underruns als Sollwert; Vergleich ohne Zugriff auf loopPlan erwartet >0.
2. Derselbe Test: Reset/Seek, alte Pakete abgelehnt, erwartete statt unerwartete Underruns und erstes Seek-Bit.
3. Vollsuite `py -3.11 -m unittest discover -s tests -v` und `node --test tests/realtime/*.test.mjs` nicht ausgeführt: Git-Checkout DNS-Fehler, keine CI-Läufe laut KETTEN.md. Kein Testerfolg behauptet.
4. Diese Datei. Soak (nicht gemessen): Performance-Profil, synthetisches Testsignal, 100 % Wet, 4-s-Loop starten; vorhandenes `benchmarks/g4/soak.js` in DevTools für 7200 s ausführen. `py -3.11 -m benchmarks.g4.report <Rohdatei> --candidate Performance --out <Ergebnisdatei>`; unexpected_underruns=0 prüfen.

Keine neuen Abhängigkeiten, Versionen/Pins/Lizenzen fremder Projekte oder Modellgewichte. Python 3.11, Node 22, CPU-Simulation. Browser/Hardware nicht gemessen. Offenes Risiko: IPC-Backpressure und tatsächliche Renderlatenz/Timer-Jitter unter realer Last, Testausführung ausstehend. Rückbau: nach AUFGABE-35 die Commits AUFGABE-34 revertieren.

## Ergänzender Prüfbeleg / Übergabe
Gezielte JS-Teilausführung: beide Tests aus `pump_loop_34.test.mjs` (Originalpumpe, AudioCore, Worklet, Transport, Ring; Assert-/Timer-Shims, DSP aus) in V8 bestanden. 100 Wechsel: 0 unerwartete Underruns, Negativkontrolle >0; manueller Seek: nur erwartete Underruns, alte Epoch abgelehnt. Regulärer Node-Lauf weiterhin offen.
Fertig: Code und Testfälle. Offen: vollständige Suite sowie Browser-/Sidecar-Last. Nächster Schritt: oben genannte Befehle beim Koordinator ausführen. Fehlerausgabe und Übergabe der gesamten Kette in AUFGABE-35.md.
