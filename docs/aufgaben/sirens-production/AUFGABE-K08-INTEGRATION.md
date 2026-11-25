# K08 – Integration: echter CLI-Durchstich, Signal-Room-Eintrag, Export

Abgespalten aus AUFGABE-K00-RUNNER.md, Umfang 3. Lies PLAN.md, CONTRACT.md, REUSE-AMM.md, KETTEN.md und die
Ergebnisdateien `ergebnisse/K00.md` bis `ergebnisse/K07.md`. Owner-Dateien wie K00 (einschließlich der
gemeinsamen Server-/Config-/Route-/CI-Dateien). PR auf integration/sirens-production.

## Ziel

Die gemergten Module K01–K07 hinter dem Runner aus K00 zu einem echten Durchlauf verbinden:
`python -m sirens.production render --brief … --mode preview|full` erzeugt mit echten Modulen (ohne Mock) einen
Run mit plan.json, assets.json, stems.json, mix.wav, master.wav, report.json und status.json.

## Umfang

1. CLI-Befehle aus CONTRACT.md („Aufrufe“) vollständig auf die Module K01–K07 verdrahten; Mock nur noch im Test.
   Fehlt eine Fähigkeit zur Laufzeit (kein Live, kein TTS-Modell, Dienst aus): klare Meldung mit genau einer
   nächsten Handlung, Standardweg rendert ohne Ableton weiter.
2. Den „Anpassungsbedarf“ aus den Ergebnisdateien K01–K07 auflösen (Vertrag nur per kurzem Contract-Abschnitt in
   CONTRACT.md ändern, Tests der betroffenen Ketten mitziehen).
3. UI-Modul aus K06 (`web/js/production.js`, `web/production.css`) als eine Signal-Room-Kachel
   „Production Engine“ einbinden (Register, Stylesheet, Server-Routen für Start/Status/Abbruch/Export,
   Ableton öffnen/übernehmen über K07). Lifecycle laut `docs/signal-room.md`. Bestehender Nachlauf-Knopf bleibt
   unverändert.
4. „Song erstellen“ als ein Klick: Preview → technische Prüfung → Vollsong ohne Pflicht-Zwischenschritt;
   „Verbessern“ mit optionalem Klartext erzeugt einen neuen Run (alte Runs unverändert).
5. Export als neue Version mit expliziter Aktion, kein Überschreiben.

## Nicht im Umfang

Keine neuen Musik-, Mix- oder Instrumentfunktionen (das bleibt bei K01–K07), keine Modell-Downloads, keine
Änderung an Realtime-GPU-Policy, kein Merge nach main.

## Abnahme

- CPU-CI ohne Netz/GPU/Live: End-to-End-Test der drei Nutzeraktionen (Song erstellen, anhören/Status,
  Ableton-Export bzw. Fallback) mit Mock-Backends; Cancel-, Crash- und Pfadtests; zwei Seeds; Teilerneuerung
  lässt alte Runs unverändert.
- Lokaler echter Lauf (Clear Head, 30–60 s Preview) als Skript/Befehl in `ergebnisse/K08.md`; „nicht gemessen“,
  bis der Koordinator ihn am Zielrechner ausführt.
- `python -m unittest discover -s tests -v` und `node --test tests/logic.test.mjs` grün.
