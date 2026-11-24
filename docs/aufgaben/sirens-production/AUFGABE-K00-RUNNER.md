# K00 – Runner, Verträge und Integration

Lies PLAN.md, CONTRACT.md, KETTEN.md. Branch/Datei-Ownership laut Register; PR auf integration/sirens-production. Start sofort mit Mocks.

1. Implementiere die CLI aus CONTRACT.md, Validatoren und Run-Verzeichnisse, atomare Manifeste/Status, Fehler/Cancel/Resume (Resume darf neuen Run erzeugen), deterministische Fixtures und Hashcache. Keine Datenbank. Minimaler Mock-Durchstich mit echten künstlichen WAVs.
2. Lese vorhandene Config, sichere Pfade und Store; keine Änderungen an produktiven Aufträgen. Adapter zur bestehenden GPU-Verwaltung, keine Umgehung exklusiver Claude-Leases; Planung und Render getrennt. Prüfe tatsächliche Worker-API und dokumentiere nötigen generativen Dateijob-Weg; kein Dummy-Audio. Separate Worker-Prozesse, begrenzte Zeit/CPU/RAM, saubere Prozessbeendigung.
3. Nach Merge K1–K6 integriere echten CLI-Durchstich, dann einen Signal-Room-Eintrag und minimalen Status/Abbruch/Export. Nur du änderst gemeinsame Server-/Config-/Register-/CI-Dateien. Export als neue Version mit expliziter Aktion, kein Überschreiben.
Abnahme: Mock-CI, reale Jobkette, negative Pfad-/Schema-/Crash-/Cancel-/Lease-Tests, zwei unterschiedliche Seeds, Teilerneuerung ohne Änderung alter Runs. G0/G2; G3 separat.

Ergebnisbericht: ergebnisse/K00.md, tatsächliche Tests, Messungen, offene Punkte. Keine Daten/Modelle im Git.
