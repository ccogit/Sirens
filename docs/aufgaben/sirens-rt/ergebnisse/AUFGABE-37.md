# Ergebnis AUFGABE-37

- PCM v1: Bit 0 (seek), unveränderte Headerbreite und Referenzbytes. Andere Bits ungültig.
- Session reicht das boolesche Seek-Feld bis zum Paket durch. Steuerwechsel leert den Sidecar über privates IPC; beim Schließen wird der Sidecar wie bisher widerrufen.
- Sidecar: zwei Generationen, Sequenz je Epoch, dritte neuere Generation entfernt nur älteste. Gemeinsames Queue- und Ratenlimit bleiben bestehen.
- Protokollbeschreibung entsprechend der ausdrücklichen Festlegung in der Aufgabe aktualisiert.

## Abnahme (Testcode vorhanden, Ausführung offen)

1. `tests/realtime/test_two_epochs.py::SidecarBoundary.test_interleaved_epochs_survive_real_sidecar` ohne expectedFailure.
2. `test_third_epoch_and_reset`: Verdrängung, alte Epoch, doppelte Seq und Steuerreset. Bestehender Backpressure-Test an die neue Semantik angepasst.
3. `test_pcm_flags`, `test_seek_type_and_pcm_flag`, `pcm_seek_37.test.mjs`, bestehende PCM-Referenztests: Flags, Seek-Feld, Bytes, Ablehnung reservierter Bits.
4. Vollsuite nicht ausgeführt: Git-Checkout scheitert mit `Could not resolve host: github.com`. Änderungen über GitHub-Datei-API gepusht. Keine CI-Läufe beim geprüften Commit 2e1571b; KETTEN.md nennt Actions als abgeschaltet. Koordinator: `py -3.11 -m unittest discover -s tests -v`, zusätzlich `node --test tests/realtime/*.test.mjs`.
5. Diese Datei.

Keine neuen Abhängigkeiten, Pins, Gewichte oder Hardwareanforderungen. Python 3.11, Node 22, CPU. Kein Hardwarewert gemessen. Risiko: reale IPC-/WebSocket-Last und vollständige Regression noch nicht geprüft. Rückbau: AUFGABE-37-Commits in umgekehrter Reihenfolge revertieren (nach Rückbau der abhängigen Aufgaben).
