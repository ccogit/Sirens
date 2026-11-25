# AUFGABE-33 – Teilstand / Übergabe

## Umsetzung
- Session.render verwaltet die letzte Seq je Audio-Epoch getrennt und hält höchstens zwei offene Audio-Epochs. Eine dritte neuere Epoch entwertet die älteste.
- Session._run prüft die Mitgliedschaft vor und nach dem Worker-Aufruf. Steuer-Epoch-Wechsel entwerten beide Generationen; bestehende Queue-Grenze bleibt erhalten.
- Optionales seek wird typgeprüft; false bleibt das bisherige PCM-v1-Verhalten. true wird ausdrücklich mit unavailable abgelehnt, solange kein zulässiges Übertragungsformat vorhanden ist.
- Der Mock-Worker prüft keine Audio-Epoch und bleibt unverändert. Bei wechselnder Epoch lädt die Worker-Schleife den Mock neu; kontinuierlicher Delay-Zustand pro Epoch ist damit nicht belegt.

## Abnahme
| Punkt | Beleg / Status |
|---|---|
| 1 | tests/realtime/test_two_epochs.py, test_alternating_epochs: echte Session-Worker-Schleife mit nachgebautem Worker und Sidecar, Paketkopf per unpack geprüft. Nicht ausgeführt. End-to-End mit echtem Sidecar offen. |
| 2 | test_third_epoch_evicts_oldest_even_in_flight: blockierter Auftrag und Queue, veraltete Epoch abgelehnt. Nicht ausgeführt. |
| 3 | test_control_epoch_discards_both: Steuer-Epoch erhöht, alter laufender und alter wartender Auftrag verworfen. Nicht ausgeführt. |
| 4 | test_seek_type_and_unavailable_until_protocol_is_extended: ungültige Typen und false geprüft; true noch nicht durchgereicht. Nicht ausgeführt. |
| 5 | Vollsuite nicht ausgeführt, kein lokaler Checkout und keine CI-Läufe. |
| 6 | Diese Ergebnisdatei. |

## Blockade und Abweichungen
Die Dateigrenze der Kette umfasst laut KETTEN.md weder sirens/realtime/sidecar.py noch sirens/realtime/pcm.py oder web/js/realtime/pcm.js.
- Hub.publish in sidecar.py verwirft bei höherer Epoch die alte Warteschlange und lehnt anschließend h["epoch"] < st.epoch ab. Damit gehen korrekt gerenderte alte Pakete nach Ankündigung der neuen Epoch verloren. test_interleaved_epochs_survive_real_sidecar dokumentiert das mit expectedFailure; nach der Korrektur den Marker entfernen.
- PCM-v1-Kopf hat kein seek-Feld, beide PCM-Validatoren erlauben nur flags=0. Ein gesetztes Flag ohne Vertragsänderung ergibt invalid; ein zusätzliches Python-Dict-Feld wird nicht serialisiert. Der bestehende Vertrag bleibt unverändert; true wird nicht als normaler Render-Auftrag verschleiert.
- PLAN.md enthält keine WP33/34/35-Abschnitte; die jeweiligen Aufgabendateien sind die konkrete Spezifikation.
- KETTEN.md Regel 4 nennt abgeschaltete GitHub Actions seit 24.11.2026, anders als der Chat-Auftrag. GitHub meldet workflow_runs=[] und statuses=[] für 15c78bca3b61c409702e2e36e15ad3f77714ac6e. CI nicht als grün ausgewiesen.

## Nachstellen
- py -3.11 -m unittest tests.realtime.test_two_epochs -v
- py -3.11 -m unittest discover -s tests -v
- Linux entsprechend python3.11 statt py -3.11.
- Kein Modell, kein Netz, keine GPU für die Tests. Keine neuen Abhängigkeiten, Pins, fremden Lizenzen oder Gewichte. Zielhardware und Browser nicht gemessen.

## Übergabe
Fertig: Teilimplementierung der Sitzungsgrenze und Regressionstests; Commit 401552faf0342014f553897f5c097bb107db43d4 und 15c78bca3b61c409702e2e36e15ad3f77714ac6e.
Offen: Sidecar muss zwei Audio-Epochs und getrennte Seq-Ordnung zulassen, ohne die alte Queue beim Öffnen der nächsten zu löschen. Seek-Metadatum benötigt eine koordinierte Vertragsfreigabe/ADR und passende Encoder/Decoder bzw. eine ausdrücklich spezifizierte alternative Steuerung; danach true bis zum Worklet belegen. Erst dann Pump- und Rate-Abnahme.
Nächster Schritt: Koordinator erweitert die Dateifreigabe bzw. liefert kompatible Änderungen; anschließend expectedFailure entfernen, echte Sidecar-Integration und bestehende Tests ausführen, dann Aufgaben 34 und 35.
Fehlerausgabe der lokalen Git-Prüfung: fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com.
Risiken: Sidecar-Drops, Delay-Reset bei wechselnder Epoch, volle Render-Queue, erste Seq muss 0 sein (bestehender Browser erhöht Seq auch bei 503), nicht ausgeführte Tests. Nicht als mergefertig betrachten.
Rückbau: Ketten-Commits revertieren; keine Änderungen an Daten oder Konfiguration.
