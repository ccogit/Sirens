# Aufgabe 37: Sidecar und PCM-Kopf für zwei Audio-Epochs und Seek

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Rest von Aufgabe 33
(gemergt ist der Teil in `sirens/realtime/sessions.py`, siehe `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-33.md`,
Abschnitt „Blockade und Abweichungen“).

## Ziel

Pakete der laufenden Audio-Epoch kommen auch dann beim Browser an, wenn die nächste Epoch schon begonnen hat.
Ein Seek ist im Paketkopf erkennbar.

## Ausgangslage

- `sirens/realtime/sidecar.py`, `Hub.publish()` (ab Zeile ~93): verwirft bei höherer Epoch die alte
  Warteschlange und lehnt danach `h["epoch"] < st.epoch` ab.
- `tests/realtime/test_two_epochs.py`, `test_interleaved_epochs_survive_real_sidecar`: mit `expectedFailure`
  markiert; der Marker fällt mit dieser Aufgabe weg.
- PCM-v1-Kopf: `sirens/realtime/pcm.py` (Zeile ~14) und `web/js/realtime/pcm.js` (Zeile ~5) erlauben nur
  `flags` = 0. Beschreibung in `docs/realtime/protocol.md`.

## Festlegung (vom Koordinator entschieden)

- `flags` Bit 0 = `seek` (Paket gehört zum ersten Block nach einem manuellen Seek). Übrige Bits bleiben 0 und
  werden abgelehnt. Das bleibt PCM v1: alte Sender schicken 0, alte Empfänger sehen nur Bit 0 neu.
- Der Sidecar hält je Stream höchstens zwei Audio-Epochs offen (laufende und nächste), mit Seq-Prüfung je Epoch.
  Eine dritte, neuere Epoch schließt die älteste.

## Umfang

1. `pcm.py` und `pcm.js`: `flags` 0 oder 1 zulassen, Feld `seek` beim Lesen ableiten; Tests für beide Seiten.
2. `sessions.py`: das schon angenommene Feld `seek` als Bit 0 in den Paketkopf schreiben.
3. `sidecar.py`: zwei Audio-Epochs je Stream wie oben; ein Steuer-Epoch-Wechsel verwirft weiter alles.
4. `docs/realtime/protocol.md`: Bit 0 beschreiben.
5. `expectedFailure` in `test_interleaved_epochs_survive_real_sidecar` entfernen; Test muss grün sein.

## Erlaubte Dateien

`sirens/realtime/sidecar.py`, `pcm.py`, `sessions.py`, `web/js/realtime/pcm.js`, `docs/realtime/protocol.md`,
Tests unter `tests/realtime/`.

## Abnahme

1. Test: Pakete von Epoch n und n+1 abwechselnd veröffentlicht, alle kommen in Seq-Reihenfolge je Epoch an.
2. Test: Epoch n+2 schließt n; Paket mit Epoch < n wird abgelehnt.
3. Test: Kopf mit `flags` 1 wird in Python und JS gelesen und geschrieben; `flags` 2 wird abgelehnt.
4. Alle bestehenden Tests bleiben grün.
5. Ergebnisdatei `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-37.md`.
