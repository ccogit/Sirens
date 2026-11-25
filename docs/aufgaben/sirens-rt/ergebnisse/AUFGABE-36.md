# AUFGABE-36 – G4-Soak und -Bericht (KETTE-57)

## Umsetzung

- Depends-on: gemergte AUFGABE-30. Keine Abhängigkeit von KETTE-56.
- `benchmarks/g4/soak.js`: je Spur getrennte Deltas der kumulativen Zähler
  `unexpectedUnderruns` und `expectedUnderruns`, einschließlich unabhängiger
  Rücksetzer (bei kleinerem Folgewert diesen addieren). Bei älterem Worklet
  wird `underruns` als unerwartet gezählt, erwartete als 0. Die Rohdatei
  enthält beide neuen Felder; das alte Feld `underruns` bleibt Alias für
  unerwartete Underruns. `rawUnderruns` ist nicht maßgeblich.
- `benchmarks/g4/report.py`: beide Zähler in JSON und in den Notizen (auch
  Markdown-Bericht). Alte Rohdateien bleiben lesbar; fehlende erwartete
  Underruns sind dort nicht getrennt erfasst (null). Der gemeinsame Messwert
  `messwerte.warm.underruns` bleibt erhalten und zählt ausschließlich
  unerwartete Underruns. `benchmarks/system_suite.py` prüft diesen Messwert
  bereits auf 0 und die belegte Dauer; kein Eingriff dort erforderlich.
- `soak_status` lautet bei vollständiger Messung und null unerwarteten
  Underruns „bestanden“, sonst „nicht bestanden“. Das übergeordnete
  `gate` bleibt absichtlich `nicht_gemessen`: der Soak allein ersetzt
  nicht die G4-Gesamtfreigabe durch den Koordinator.
- Integration ohne Force-Push als Merge-Commit 28da50012e7f6ab8091faaef91b44be5398053d5
  (Integrationsstand 50736019cc72e9241a7638c27678378eb7b354c3).
  Kein eigener Eingriff in Register, Board, Produktcode oder fremde Tests.

## Abnahmepunkte

| Punkt | Beleg / Stand |
|---|---|
| 1 – Erwartete und unerwartete Underruns | `tests/realtime/test_g4_underruns_36.py`: expected_only_passes_and_is_reported / one_unexpected_fails_even_with_expected; synthetische Rohdaten 128 erwartete, 0 bzw. 1 unerwartete. Beide Tests bestanden. |
| 2 – Altes Rohformat | test_legacy_format (0/1 alte Underruns), bisheriger test_g4_report.py sowie Node-Test mit ausschließlich alten Worklet-Zählern: bestanden. |
| 3 – Regression | 7 isolierte Python-Tests (6 neu, 1 bestehend) bestanden; 3 Node-Tests bestanden (siehe unten). Vollsuite unter Python 3.11 / Windows nicht ausgeführt; CI laut KETTEN.md abgeschaltet, API liefert keine Workflow-Läufe/Statuschecks. |
| 4 – Ergebnisdatei | diese Datei. |

Weitere Tests: Vorrang expliziter Felder, ungültige Zähler, unvollständige
Messung; Node-Mock des unveränderten Soak-Snippets mit mehreren Spuren,
Rücksetzern, Altformat und fehlerhaftem Zähler.

## Prüfung / Nachstellen

Isoliert lokal: Node 22.16.0, Python 3.13.5 (nicht die Zielversion).
Die aus dem Connector übernommenen Dateien (Soak, Report, neue Tests,
bestehender G4-Test und result.py) wurden per Git-Blob-SHA gegen den
Repository-Stand abgeglichen. Für den Python-Import wurde ausschließlich
baseline.collect als nicht aufgerufener lokaler Stub bereitgestellt; keine
Rechnerdatenerfassung oder CLI-Ausführung in diesem isolierten Test.
Ausgaben:

- `node --test tests/realtime/g4_underruns_36.test.mjs`: 3 pass, 0 fail.
- `python -m unittest discover -s tests/realtime -p 'test_g4*.py' -v`:
  Ran 7 tests, OK (einschließlich bisherigem G4-Report-Test).

Zielprüfung im vollständigen Checkout durch den Koordinator:

```powershell
py -3.11 -m unittest discover -s tests -v
node --test tests/realtime/g4_underruns_36.test.mjs
```

**Hardware: nicht gemessen.** Windows 11 / RTX 5080 / Browser mit
Audioausgabe. Performance-Profil, synthetisches Testsignal, 100 % Wet,
4-s-Loop, DevTools-Snippet `benchmarks/g4/soak.js` ausführen, 7200 s wählen.
Rohdatei außerhalb des Repositorys speichern:

```powershell
py -3.11 -m benchmarks.g4.report C:\TEMP\wp19-soak-roh.json --candidate Performance --out C:\TEMP\g4-result.json
py -3.11 -m benchmarks.result C:\TEMP\g4-result.json --markdown C:\TEMP\g4-result.md
```

Keine neuen Abhängigkeiten, Fremdprojekte, Modellrevisionen, Pins oder
Lizenzen. Tests benötigen weder Netz noch GPU noch Modellgewichte.

## Risiken, Abweichungen, Rückbau

- Alter Worklet-Stand kann erwartete Lücken nicht separat ausweisen; alte
  Underruns werden konservativ als unerwartet gezählt. Bei einer alten
  Rohdatei wird der erwartete Zähler ausdrücklich als unbekannt ausgewiesen.
- Wie bisher kann ein Zählerrücksetzer zwischen zwei Stichproben nicht
  rekonstruiert werden, wenn der neue Zähler den alten bereits überholt hat.
- Messdauer und Abschluss bleiben notwendige Bedingungen; hörbare/analoge
  Aussetzer sowie weitere G4-Kriterien sind unabhängig zu prüfen.
- Rückbau: nur eigene AUFGABE-36-Änderungscommits revertieren, nicht den
  Integrationsmerge oder fremde Änderungen.

## Übergabe

**Fertig:** Umsetzung, getrennte Soak-Wertung, Altformat und Regressionstests,
isolierte G4-Tests nachweislich bestanden.

**Offen:** vollständige Suite auf Python 3.11 / Windows sowie echte G4-Messung
und Gesamtfreigabe. Keine grüne CI behauptet.

**Nächster Schritt:** PR #81 prüfen, oben genannten vollständigen Testlauf
ausführen und G4-Soak auf dem Zielrechner nach Integration der parallelen
Kette wiederholen.

**Fehlerausgabe:** lokaler Git-Zugriff:
`fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`.
Python 3.11 lokal nicht vorhanden. CI deaktiviert (KETTEN.md, Regel 4);
Workflow- und Statusabfrage lieferten leere Listen. Ein lokaler Zwischenfehler
im Node-Mock (`Cannot access 'AudioCore' before initialization`) wurde mit
Commit 10c10ac729556ab868e6a607cca52f0300457527 behoben; Wiederholung 3/3 grün.
