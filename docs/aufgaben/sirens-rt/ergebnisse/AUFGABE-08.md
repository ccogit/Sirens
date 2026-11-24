# AUFGABE-08 – WP08 Advanced Stem Studio (Übergabe)

Depends-on: WP03; G1 RoFormer offline durch Koordinator freigegeben. DrumSep nicht freigegeben.

## Umgesetzt

- Separater Standardbibliothek-Adapter mit Modellliste, SHA-256 der Quelle, Revision und kanonischen Parametern im Cache-Schlüssel; private temporäre Ausgabe und Verzeichnis-Rename nach WAV-Prüfung. Injizierte Trenner, Fallback auf htdemucs (nur wenn injiziert); alte API unverändert.
- RoFormer-Dateilauf aus dem gepinnten MSST-Pfad mit SHA-256/Größenprüfung, sauberem Git-Checkout, weights_only=True, strict state dict, CUDA-Peak-Messung und Descriptor. Instrumental ist Residuum (Original minus Vocals), keine zweite Modellvorhersage. DrumSep nur abgeschaltete Option, keine Kick/Snare/Hi-Hat.
- Eigenes ES-Modul für A/B, Solo/Mute/Gain und WAV-Export; Hook beschreibt noch nötigen Einbau. Kein zusätzlicher AudioContext.
- Qualitätsbericht-Skript für PCM16/24 mit Referenzen und Rekonstruktions-RMS, Referenzfehler, Leakage-Projektion (orthogonale Signale erforderlich), begrenzter Lag-Suche.

## Abnahme

1. tests/realtime/test_stem_adapter.py enthält Cache-Treffer, Revisions-/Parameterwechsel, Abbruch ohne Publikation, abweichende Framezahl und injizierten Demucs-Fallback. Framezahlprüfung belegt keine tatsächliche Phasen-/Sampleausrichtung; diese muss gemessen werden.
2. Negativtests: unbekannte Modell-ID und ausgeschalteter DrumSep ohne Einzelstems.
3. tests/test_stems.py unverändert, nicht geprüft.
4. Echtes Modell, Peak-VRAM, Rekonstruktions-/Leakage-/Alignment-Bericht und Browser-Hörprüfung: **nicht gemessen**. Auf Zielrechner vorhandene geprüfte Spike-Umgebung verwenden (MSST im sys.prefix/msst; Gewichte lokal). Expliziter Aufruf:
   
       <Worker-Python> workers/separation/roformer.py <lokales-44100Hz-Stereo-WAV> <leeres-externes-Verzeichnis> --weight <lokales-MelBandRoformer.ckpt> --descriptor <externe-descriptor.json>
       python -m benchmarks.separation.quality <Original.wav> <vocals.wav> <instrumental.wav> <Referenz-Vocals.wav> <Referenz-Instrumental.wav> <externes-Ergebnis.json>
       python -m benchmarks.result <externes-Ergebnis.json>

   Referenzen müssen samplegleich gemischt sein (orthogonale Komponenten für Leakage); echte Stems zusätzlich mit lizenzierten lokalen Referenzen prüfen. Keine Audiodateien einchecken. Descriptor separat prüfen; Peak ist torch.cuda.max_memory_allocated in Byte.
5. CI: beim letzten abgefragten Stand d37b63ffbffae7d30a5dab56b6d43f2ee5de881b lieferte die GitHub-Abfrage workflow_runs=[] und statuses=[]. Kein grüner Nachweis, keine Fehlerlogs. Vollständiger lokaler Checkout/Tests nicht ausgeführt. Nachstellen: python -m unittest discover -s tests -v (Python 3.11, Node 22). board.md unverändert entsprechend Kettenregel. Node-Test: node --test tests/realtime/advanced_stems.test.mjs.

## Versionen, Grenzen und Risiken

MSST 1523206d12a521bdb20673726562524cf0f9635b (Code MIT); KimberleyJSN/MelBandRoformer Gewicht MIT laut Spike-Manifest (SHA-256 87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e). Torch/Torchaudio 2.7.1+cu128; direkte Pins in requirements.lock; transitive Pins noch nicht fest. Demucs 4.0.0 (Code MIT; vorhandene Gewichte separat prüfen) nicht in RoFormer-Umgebung, Windows diffq-Buildproblem. DrumSep-Gewichtslizenz ungeklärt. RTX 5080 16 GB Ziel; realer Peak unbekannt. Kein Streaming. Der Adapter-Prototyp prüft PCM-WAV; MP3/FLAC/Resampling und große Dateien offen. Korrupten bestehenden Cache manuell bereinigen; pro Instanz serialisiert, noch kein Prozess-übergreifender Lock. UI-Hook noch nicht eingebaut; Exportziel muss Controller absichern. Modellmetadaten sind noch kein vom ModelRegistry geladenes v1-Manifest.

## Übergabe

Fertig: oben genannte Teilmodule und Tests gepusht. Offen: produktive Verdrahtung der Trenner, insbesondere Demucs-Bestand und RoFormer mit GPU-Lease, Prozessbaum-Abbruch, Installation/Probe und Capability-Registry; Tests für Worker/Benchmark, geeignete Referenz-Fixtures, tatsächliche Sampleausrichtung, Route/UI-Einbau und CI-Nachweis.

Nächster Schritt: Offline-Dateijob-Transport mit Koordinator abstimmen. Der eingefrorene WorkerSupervisor.request akzeptiert keine Pfadparameter und maximal 1 MiB PCM je Frame; eine ganze Songdatei passt nicht. Kein Umgehen des GPU-Managers; ADR für nötige Vertragserweiterung oder gekapselten Dateijob-Adapter erstellen. Danach reale Runner in StemAdapter injizieren und Fallback/Fehler/Abbruch sowie Zielhardware prüfen. Hook WP08 beachten. CI des PR erneut abfragen und Fehler korrigieren. Kein Merge vor abgeschlossener Abnahme.

Fehlerausgabe/Blockade: keine CI-Ausgabe abrufbar (workflow_runs=[], statuses=[]); fehlender kompatibler Dateijob-Transport und nicht fertig integrierter Umfang. Kein erfolgreicher Modell- oder Testlauf behauptet.

Rollback: PR nicht mergen bzw. nur WP08-Dateien revertieren; Bestandsdateien unverändert, keine Downloads oder Modellgewichte im Repo.
