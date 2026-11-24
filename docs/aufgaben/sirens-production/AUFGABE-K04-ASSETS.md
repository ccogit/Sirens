# K04 – Generative Klangbausteine und Spoken Word

Lies PLAN.md, CONTRACT.md, KETTEN.md. Branch/Datei-Ownership laut Register; PR auf integration/sirens-production. Start sofort mit Mocks.

1. Nutze vorhandenen Stable-Audio-Small-Worker soweit dessen geprüfter Jobpfad passt. Erzeuge kurze Foley/Textures/Fills/Loops mit explizitem Prompt/Seed; Glockenboje, Möwen, Nebelhorn und Schiffsglocke als erste Assets. Prüfe Audiodauer, Tempo/Tonart soweit relevant, Artefakte und Seam-Cuts. Echte lizenzierte Samples alternativ; nicht automatisch aus Referenzsongs extrahieren.
2. Prüfe ein lokales neuronales TTS (Qwen3-TTS als Kandidat, Hardware-/Lizenz-Gate). Ruhige nahe männliche englische Sprechstimme, exakt vorgegebener Text, kein Gesang; Timing mit K2 abstimmen, leichte Pausen statt Zeitkompression. Keine unbefugte Stimmkopie. Verfügbarkeit/fehlende Modelle sichtbar; kein eSpeak als Qualitätsersatz.
3. Liefere assets.json, einzelne WAVs, Lizenz-/Provenienz-Manifest, optional ASR-Abgleich und Hörprobe. Caches, Timeout/Abbruch. GPU-Lease über A0; Code parallel, reale Inferenz einzeln. Stable Audio Modellgewichte nur mit bestätigter Lizenz; kommerzielle Nutzung separat prüfen.
Abnahme: Offline-Mock-Tests, mindestens drei reale Klangbausteine und ein vollständiger Spoken-Cue auf Zielhardware oder dokumentierter Blocker; WAV-/Hash-/Lizenzprüfung, keine ungewollte Cloud. G1.

Ergebnisbericht: ergebnisse/K04.md, tatsächliche Tests, Messungen, offene Punkte. Keine Daten/Modelle im Git.

Ableton: Assets als einzeln austauschbare, lizenzierte WAV-Dateien mit stabilen IDs liefern; K07 kann sie ohne Modellinstallation in Live nutzbar machen. Keine Live-spezifische Parallelentwicklung.

## Verbindliche Wiederverwendung (Revision)

Lies REUSE-AMM.md vor der Umsetzung. K04: zuerst SecondRoom vorhandene deliver_generate/list/job/used, AMM Sample-DB, Signature-Kits und KETTE-98 (tatsächlich vorhandene Endpunkte prüfen). Keine neue Sample-Bibliothek oder ACE-Engine, ACE nicht Pflicht. Lizenz/Guard/Hostpfad/Jobstatus der vorhandenen Dienste beibehalten. Stable Audio und TTS nur für belegte Lücken.
