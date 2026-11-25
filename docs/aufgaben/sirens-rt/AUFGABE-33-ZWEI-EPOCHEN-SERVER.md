# Aufgabe 33: Server rendert alte und nächste Audio-Epoch nebeneinander

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt die gemergte
Aufgabe 30 voraus. Folgeaufgabe aus der Übergabe in `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-30.md`.

## Ziel

Der Server verwirft beim ersten Render-Auftrag einer neuen Audio-Epoch nicht mehr die laufenden Aufträge der
bisherigen. Nur so kann der Browser den Wet-Puffer für die Zeit nach einem Loop-Sprung vorfüllen, während die
alte Generation bis zum Sprung weiterläuft (Grundlage aus Aufgabe 30: zwei Wet-Ringe im Worklet).

## Ausgangslage

- `sirens/realtime/sessions.py`, `Session.render()`: lehnt `audio_epoch < self.audio_epoch` mit
  `stale_epoch` ab und setzt `self.audio_epoch = audio_epoch` beim Annehmen.
- `Session._run()` (Worker-Schleife): verwirft jeden Auftrag mit `audio_epoch != self.audio_epoch`, auch einen
  bereits laufenden. Damit endet die alte Generation, sobald die neue angekündigt ist.
- Vertrag: `docs/realtime/` (Epoch/Seq-Prüfung, veraltete Pakete werden verworfen). Der Vertrag bleibt gültig.

## Umfang

1. Der Server hält höchstens **zwei** Audio-Epochs gleichzeitig offen: die laufende und die nächste.
   Aufträge beider werden angenommen und in Seq-Reihenfolge je Epoch gerendert. Eine dritte, neuere Epoch
   schließt die älteste; deren noch offene Aufträge werden verworfen.
2. Seq-Prüfung je Audio-Epoch getrennt (`render_seq` je Epoch), Seq beginnt je Epoch bei 0.
3. Ein Steuer-Epoch-Wechsel (`epoch`, z. B. Seek, Stopp) verwirft weiter alles, wie heute.
4. Ein Feld `seek` (bool, optional) im Render-Auftrag wird angenommen und unverändert in den Paketkopf
   übernommen, damit der Worklet die Lücke als *erwarteten* Underrun zählen kann. Fehlt es: `false`.
5. Mock-Worker (`workers/mock/worker.py`) nur anpassen, falls er die Audio-Epoch selbst prüft.

## Nicht im Umfang

- Browser-Seite (`web/js/realtime/shell.js`): Aufgabe 34 in derselben Kette.
- Abtastraten: Aufgabe 35.

## Abnahme

1. Test (`tests/realtime/test_two_epochs.py`): Aufträge für Epoch n und n+1 abwechselnd eingereicht, beide
   werden vollständig gerendert; Pakete tragen die richtige Epoch und Seq.
2. Test: Epoch n+2 verwirft offene Aufträge von n; Auftrag mit Epoch < n wird mit `stale_epoch` abgelehnt.
3. Test: Steuer-Epoch-Wechsel verwirft beide offenen Audio-Epochs.
4. Test: `seek` wird durchgereicht; ungültiger Typ ergibt `invalid`.
5. Alle bestehenden Tests bleiben grün (`py -3.11 -m unittest discover -s tests`).
6. Ergebnisdatei `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-33.md`.
