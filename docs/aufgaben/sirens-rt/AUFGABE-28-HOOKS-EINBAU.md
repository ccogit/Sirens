# Aufgabe 28: Alle offenen Hooks in die Oberfläche einbauen

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt die gemergten
Aufgaben 07, 08/25, 11, 12/27, 13, 15, 17/26 und 18 voraus.

## Ziel

Jede gemergte Funktion ist im RTX Neural Lab bedienbar: über einen gemeinsamen Player, eine gemeinsame Panic
und klare Zustände. Nicht freigegebene Modelle erscheinen mit Grund („nicht installiert“, „nicht gemessen“).

## Ausgangslage

- Hooks unter `docs/realtime/hooks/`: WP07 (DEMON), WP08 und WP25 (Stem Studio, Dateijob), WP09 (DSP-Rack),
  WP11 (RAVE/AFTER), WP12 und WP27 (Pads), WP13 (Semantic Stems), WP14 (Performance-Tools), WP15 (Companion),
  WP18 (Infinite Mutation). Offene Punkte stehen in `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-*.md`,
  Abschnitte „Übergabe“ und „Anpassungsbedarf“.
- Lab Shell: `web/js/realtime/shell.js`, `controls.js`, `capabilities.js`, `gpu_panel.js`; Audio-Kern
  `web/js/realtime/audio_core.js`; Adressen `sirens/realtime/routes.py`, `sessions.py`.

## Umfang

1. Jeden Hook umsetzen; wo ein Hook fehlt oder unklar ist, den Einbau aus dem Modul selbst ableiten.
2. Ein gemeinsamer Player und eine gemeinsame Panic für alle Module; nur ein aktiver Ausgabepfad.
3. Fähigkeiten aus der Registry: verfügbar, nicht installiert, nicht gemessen (Gate fehlt in
   `benchmarks/results/g1/`), Fehler – jeweils mit Text und abgeschaltetem Bedienelement.
4. Dynamische Regler aus dem Capability-Descriptor (RAVE-Latents, DEMON-Parameter, Companion-Stil).
5. Diese Aufgabe darf alle gemeinsamen Dateien ändern.

## Nicht im Umfang

- GPU-Regel, Profile und Supervisor-Lebenszyklus (Aufgabe 29, parallel). Modell-Worker selbst.
  Katalog-API und Song-/Albumliste.

## Abnahme

1. Node-Tests je Modul: Bedienelement sichtbar, Zustand je Fähigkeit korrekt, Panic stoppt alles.
2. HTTP-Test: kompletter Ablauf mit Mock-Workern ohne Leck nach Verlassen.
3. CI des PR grün.
