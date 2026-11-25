# Aufgabe 30: Nahtloser Loop- und Epoch-Wechsel im Wet-Pfad

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt die gemergten
Aufgaben 04 und 06 voraus. Folgeaufgabe aus der Systemabnahme G4 (Aufgabe 19).

## Ziel

Der Wet-Pfad läuft über Loop-Sprünge und Epoch-Wechsel ohne Lücke. Gate G4 verlangt null unerwartete
Underruns in 2 Stunden; heute fehlen bei **jedem** Loop-Sprung rund 75 ms Wet-Audio.

## Ausgangslage

- G4-Messung am 24./25.11.2026 (RTX 5080, Live Lab → RTX Neural Lab, Profil Performance, Quelle
  „Synthetisches Testsignal (Mock)“, Dry/Wet 100 %, 4-s-Loop, 7200 s): 6.516.288 Underrun-Frames bei 1.800
  Epoch-Wechseln, also etwa 3.620 Frames (≈ 75 ms bei 48 kHz) je Wechsel. Ohne Epoch-Wechsel (G2, WP04): 0.
- Ursache laut Code:
  - `web/js/realtime/worklet_processor.js`, `process()`: Bei `frame===this.nextLoop` erhöht der Worklet
    selbst `this.epoch` und ruft `paths[j].reset(this.epoch, frame)` auf. Damit ist der Wet-Puffer leer.
  - `web/js/realtime/audio_core.js` erfährt den neuen Epoch erst über die `status`-Abfrage alle 20 ms
    (`setInterval`) und setzt dann erst die `Transport`s zurück.
  - Der Produzent (Mock-Worker bzw. Modell über `transport.js`) liefert erst danach Daten mit dem neuen Epoch,
    plus Verarbeitungslatenz.
- Grundlage: `web/js/realtime/ringbuffer.js`, `transport.js`, `clock.js`, `pcm.js`, `mock_api.js`,
  `workers/mock/`, Soak `benchmarks/g4/soak.js`, `benchmarks/g2/`.
- Nebenbefund: Der Mock-Pfad im Live Lab verlangt 48 kHz. Ausgabegeräte laufen oft mit 44,1 kHz; G4 musste
  per Init-Skript einen 48-kHz-AudioContext erzwingen.

## Umfang

1. Loop-Sprünge vorausplanen statt nachträglich zurücksetzen: Der Hauptthread kennt Loop-Länge und
   Startframe. Er kündigt den nächsten Epoch rechtzeitig an, und der Produzent füllt den Wet-Puffer für die
   Zeit nach dem Sprung vor (Pre-Roll mindestens Puffergröße plus Modelllatenz). Die Umsetzung ist frei
   wählbar, solange der Vertrag aus `docs/realtime/` gilt (Epoch/Seq-Prüfung, veraltete Pakete werden
   verworfen). Ein Vorschlag: zwei Puffergenerationen je Pfad im Worklet, Umschalten exakt am Loop-Frame.
2. Manuelle Seeks dürfen eine kurze, erwartete Lücke haben. Sie werden als *erwartete* Underruns gezählt
   (`expectedUnderruns`), nicht als unerwartete. Die Unterscheidung muss im Status sichtbar und getestet sein.
3. Mock-Pfad mit der Abtastrate des Geräts (44,1 kHz und 48 kHz) betreiben, ohne erzwungenen
   48-kHz-Kontext.
4. `benchmarks/g4/soak.js` und `benchmarks/g4/report.py` weisen unerwartete und erwartete Underruns getrennt
   aus. Für die G4-Wertung zählen nur die unerwarteten.

## Nicht im Umfang

- DSP-Rack und Steuerlatenz (Aufgabe 31, parallel). `web/js/realtime/effects/` nicht ändern.
- Mess-Harness außerhalb von `benchmarks/g4/` (Aufgabe 32, parallel).

## Abnahme

1. Node-Test mit nachgebautem Worklet-Takt: 4-s-Loop über 100 Wechsel mit Produzent mit 50 ms Latenz
   ergibt 0 unerwartete Underruns. Der heutige Stand im selben Test ergibt mehr als 0 (Regressionsbeleg).
2. Test: Manueller Seek zählt höchstens als erwarteter Underrun. Veraltete Pakete (alter Epoch) werden
   weiter verworfen.
3. Test: Mock-Pfad bei 44,1 kHz und 48 kHz.
4. Alle bestehenden Tests unter `tests/realtime/` bleiben grün (`py -3.11 -m unittest discover -s tests` und
   die Node-Tests).
5. Ergebnisdatei `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-30.md` mit Ansatz, Testbelegen und dem Befehl für
   den Soak-Nachlauf. Den Soak selbst führt der Koordinator aus.
