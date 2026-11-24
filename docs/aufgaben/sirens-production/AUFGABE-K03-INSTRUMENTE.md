# K03 – Professionelle Instrumente und Offline-Rendering

Lies PLAN.md, CONTRACT.md, KETTEN.md. Branch/Datei-Ownership laut Register; PR auf integration/sirens-production. Start sofort mit Mocks.

1. Prüfe gemeinsam mit K07 vorhandene Ableton-Instrumente und einen verifizierten automatischen Live-Renderpfad. Ohne positiven Spike verwende genau einen eigenständigen Offline-Host (z.B. Surge XT + DawDreamer/anderer nachweisbarer Host), ohne Ableton zu erzwingen. Kein REAPER-Zwang. K07 besitzt den Ableton-Adapter; K03 integriert nur dessen Vertrag und kann mit Mock parallel starten. Maximal zwei kurze Spikes; wähle einen Weg anhand echter Renderqualität, Installation, Lizenz, Headroom, Reproduzierbarkeit. Kein VST-Wrapper-Rewrite. Inventar lokal vorhandener Instrumente und Samples; keine automatischen Downloads.
2. Semantisches Patch-Manifest für tight kick, mono sub, mechanischen funk bass, metallischen Hook, Percussion, Mandoline/Cello (Multisamples, Artikulation/Velocity/Round-robin falls vorhanden). Render MIDI/Automation aus Plan, platziere K4-Assets samplegenau, exportiere ausgerichtete Stems. Mono-Sub, Sidechain-Steuersignal, Timing/Level kontrollieren. Optional kurzer Wet/Dry-Vergleich; keine Demo als professionelles Ergebnis ausgeben.
3. Rendern einzelner Tracks und Abschnitte mit Cache; Backend/version/preset/seed in Manifests. Mock-only Fallback für Tests, fehlende echte Instrumente ehrlich melden.
Abnahme: deterministische Fixture-Tests, gemessene 126 BPM/Beatpositionen, echte 30–60-s-Grooves mit drei Varianten und hörbar unterschiedlichen Presets, Lizenzstatus, Host-Kompatibilität Windows. G1 Hörvergleich.

Ergebnisbericht: ergebnisse/K03.md, tatsächliche Tests, Messungen, offene Punkte. Keine Daten/Modelle im Git.

Ableton: pro Instrument vollständiges ausgerichtetes Audio und MIDI/Automation/semantische Patch-ID für K07 liefern. Kein doppeltes MIDI+Audio im Set. Native Live-Instrumente nur nach nachgewiesenem Adapter; bei manueller Live-Bearbeitung keine automatische Überschreibung. Host-Auswahl intern.
