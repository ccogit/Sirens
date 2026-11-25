# Aufgabe 34: Browser-Pumpe füllt den Wet-Puffer vor dem Loop-Sprung vor

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt Aufgabe 37 (in
derselben Lane davor) sowie die gemergten Aufgaben 30 und 33 voraus. Erlaubte Dateien: `web/js/realtime/shell.js`,
`audio_core.js`, `transport.js`, Tests unter `tests/realtime/`.

## Ziel

Der Wet-Pfad läuft über Loop-Sprünge ohne unerwartete Lücke. Gate G4 verlangt null unerwartete Underruns in
2 Stunden; im G4-Lauf vom 24./25.11.2026 fehlten bei jedem Loop-Sprung rund 75 ms Wet-Audio.

## Ausgangslage

- Aufgabe 30 hat geliefert: zwei Wet-Ringe im Worklet mit Umschalten am Loop-Frame
  (`web/js/realtime/worklet_processor.js`), `loopPlan` mit Epoch, Frame, Quelle und Vorlauf sowie getrennte
  Transport-Credits und Sequenzen (`web/js/realtime/audio_core.js`), Zähler `expectedUnderruns` und
  `unexpectedUnderruns` im Status. Test: `tests/realtime/loop_epoch_30.test.mjs`.
- Offen laut Übergabe: `web/js/realtime/shell.js`, Funktion `pump()` (ab Zeile ~156) nutzt den Plan nicht. Sie
  wechselt erst, wenn `core.clock.epoch` schon gestiegen ist (Zeile ~162), also nach dem Sprung.
- Aufgabe 33 (gemergt) und 37 (davor in dieser Lane): Server und Sidecar führen laufende und nächste
  Audio-Epoch nebeneinander, Seq je Epoch ab 0, Seek als Bit 0 in `flags`.

## Umfang

1. `pump()` rendert die laufende Generation bis zum Loop-Ende und beginnt, sobald `loopPlan` den Sprung
   ankündigt, die nächste Generation (Audio-Epoch + 1, Seq ab 0, Quelle und Ausgabeframe aus dem Plan) mit
   einem Vorlauf von mindestens Puffergröße plus gemessener Renderlatenz.
2. Manueller Seek: Render-Aufträge tragen `seek: true`; die Lücke zählt als erwarteter Underrun.
3. Node-Test mit nachgebautem Takt aus Worklet, AudioCore, Pumpe und Produzent mit 50 ms Latenz (das, was in
   Aufgabe 30 als „vollständige Produzenten-/Worklet-Taktsimulation offen“ steht): 4-s-Loop über 100 Wechsel.

## Nicht im Umfang

- Abtastrate des Geräts: Aufgabe 35 (danach in dieser Kette).
- G4-Auswertung: Aufgabe 36 (eigene Kette).

## Abnahme

1. Node-Test: 100 Loop-Wechsel ergeben 0 unerwartete Underruns; derselbe Test mit der alten Pumpe (Wechsel
   erst nach dem Sprung) ergibt mehr als 0 (Regressionsbeleg).
2. Node-Test: Seek zählt nur erwartete Underruns; Pakete alter Epochs werden verworfen.
3. Alle bestehenden Tests bleiben grün (Python-Suite und `node --test tests/realtime/`).
4. Ergebnisdatei `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-34.md` mit dem Soak-Befehl für den Koordinator.
