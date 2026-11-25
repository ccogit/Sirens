# AUFGABE-34 – offen / Übergabe

Nicht begonnen: Aufgabe 33 ist an der Dateigrenze des Sidecars und dem unveränderten PCM-v1-Vertrag blockiert (siehe AUFGABE-33.md). Der bestehende Sidecar verwirft Pakete der laufenden Epoch, sobald die nächste geöffnet wird. Ein Pump-Vorlauf allein behebt das nicht.

## Abnahme
1. 100 Loop-Wechsel / alte Pumpe als Negativkontrolle: nicht umgesetzt, nicht geprüft.
2. Seek/erwartete Underruns: nicht umgesetzt, nicht geprüft.
3. Vollsuite/Node: nicht geprüft (kein Checkout; GitHub Actions abgeschaltet, keine Läufe).
4. Diese Ergebnisdatei. G4 nicht gemessen.

## Übergabe
Fertig: keine Änderungen am Browser. Offen: nach Korrektur von 33 laufenden und nächsten Plan getrennt verwalten, loopPlan nutzen, Vorlauf einschließlich Renderlatenz und Paket-/Credit-Grenzen beachten, Seek markieren, 50-ms-Produzentensimulation mit 100 Loop-Wechseln und Negativkontrolle erstellen.
Nächster Schritt: nach Freigabe und Abschluss von 33 in shell.js umsetzen; Node-Test unter tests/realtime/ und py -3.11 -m unittest discover -s tests -v ausführen.
G4 für Koordinator (nicht gemessen): Performance, synthetisches Testsignal, 100 % Wet, 4-s-Loop; vorhandenes benchmarks/g4/soak.js in DevTools für 7200 s verwenden, anschließend py -3.11 -m benchmarks.g4.report <Rohdatei> --candidate Performance --out <Ergebnisdatei>. Kein Eingriff in benchmarks/g4/.
Fehlerausgabe: siehe 33 (DNS-Fehler beim Git-Zugriff; CI-Laufliste leer).
Keine neuen Abhängigkeiten, Pins oder Lizenzen; kein Rückbau nötig.
