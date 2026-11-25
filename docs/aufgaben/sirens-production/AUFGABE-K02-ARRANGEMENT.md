# K02 – Komposition, Groove und Dramaturgie

Lies PLAN.md, CONTRACT.md, KETTEN.md. Branch/Datei-Ownership laut Register; PR auf integration/sirens-production. Start sofort mit Mocks.

1. Implementiere Plan-Validator-nahe musikalische Hilfen und Agenten-Playbook: strukturierte Übersetzung aus Stil/Negativ-Tags/Lyrics/Referenzprofil zu Abschnitten, Rollen, Noten, Grooves, Automation, Asset-Requests. Keine generische Akkordschleife als Universalantwort. Agent schreibt JSON/MIDI-Events statt Code. Musikalische Entscheidungen dokumentieren; BPM/Key-Wünsche respektieren, kontrolliertes Microtiming ohne Kick/Sub-Drift.
2. Erstelle drei Clear-Head-Groove-Varianten: Bassmechanik/Boje im Zentrum, unterschiedliche Synkopen, Register, harmonische Spannung; Stereo-Beam taktgenau ohne Sub zu verbreitern. Vollsongplan mit exakten Spoken-Cues und drei Interludes. Testbrief BRIEF-CLEAR-HEAD.md. Kein Sample-/Melodie-Kopieren.
3. Unterstütze gezielte Änderung einzelner Tracks/Sections; stabile IDs, Seeds, nachvollziehbare Unterschiede. Weitere zwei kontrastierende Briefs nach K1 erst lokal.
Abnahme: Validierung, taktgenaue Events/Automation, keine abgeschnittenen Lyrics, reproduzierbarer Plan und Varianten, Render mit K3/K4 nach Integration; musikalische Qualität per G1/G3, nicht nur Testpass.

Ergebnisbericht: ergebnisse/K02.md, tatsächliche Tests, Messungen, offene Punkte. Keine Daten/Modelle im Git.

Ableton: stabile Trackrollen, MIDI-Events, Locator-Abschnitte und Automation so planen, dass K07 sie ohne Neuinterpretation exportieren kann. Semantische Patches statt Ableton-spezifischer Pfade; vorhandene Live-Instrumente bevorzugen, wenn K07 sie nachgewiesen hat. Die Nutzerentscheidung bleibt musikalisch (Klartext), nie technisch.

## Verbindliche Wiederverwendung (Revision)

Lies REUSE-AMM.md vor der Umsetzung. K02: bestehende AMM tools/production/planner.py, harmony_tools.py, relational_groove.py, phrase_variation.py, motif_development.py und knowledge.py prüfen/wiederverwenden. Producer Pal als Live-Ausführer über Claude, Codex liefert Plan/MIDI und Review. Kein generischer neuer Musikplaner, wenn vorhandener reicht.
