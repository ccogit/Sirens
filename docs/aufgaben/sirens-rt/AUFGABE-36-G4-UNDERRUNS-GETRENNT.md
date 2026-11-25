# Aufgabe 36: G4-Soak und -Bericht trennen erwartete und unerwartete Underruns

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt die gemergte
Aufgabe 30 voraus (Abnahmepunkt 4 dort ist offen geblieben).

## Ziel

Die G4-Wertung zählt nur unerwartete Underruns. Erwartete (nach manuellem Seek) werden ausgewiesen, aber
nicht gewertet.

## Ausgangslage

- Der Worklet meldet je Stream `unexpectedUnderruns`, `expectedUnderruns` und `rawUnderruns`
  (`web/js/realtime/worklet_processor.js`, Statusmeldung ab Zeile ~112); `underruns` ist dort jetzt gleich
  `unexpectedUnderruns`.
- `benchmarks/g4/soak.js` summiert nur `underruns` (Zeilen ~27–29); `benchmarks/g4/report.py` wertet nur
  `underruns` (Zeilen ~18–26).

## Umfang

1. `soak.js` summiert `unexpected_underruns` und `expected_underruns` getrennt (Zählerrücksetzer wie heute
   behandeln). Fehlen die neuen Felder (älterer Stand), gilt `underruns` als unerwartet.
2. `report.py` weist beide aus; G4 besteht nur mit 0 unerwarteten. Altes Rohformat bleibt lesbar.
3. Nur `benchmarks/g4/` und eigene Tests ändern.

## Abnahme

1. Test: Rohdatei mit erwarteten, aber ohne unerwartete Underruns ergibt „bestanden“; mit einem unerwarteten
   „nicht bestanden“.
2. Test: Rohdatei im alten Format wird gelesen wie bisher.
3. Alle bestehenden Tests bleiben grün.
4. Ergebnisdatei `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-36.md`.
