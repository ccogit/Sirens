# AUFGABE-25 – Advanced Stem Studio Teil 2 (ÜBERGABE)

WP08 (Rest), KETTE-28. Depends-on: KETTE-26 gemergt, ADR 0006 angenommen,
G1 RoFormer offline freigegeben durch Koordinator. DrumSep nicht freigegeben.

## Umgesetzt

- Dateijob im Supervisor: serverseitige Quellen- und Ausgabegrenzen, Capability-Parameter,
  Heartbeat-Fortschritt, Deadline, Abbruch über vorhandenen Prozessbaum und private
  Ausgabe, Prüfung auf vollständige Dateiliste und Fremddateien, atomarer Rename.
- RoFormer-Worker mit Registry-Manifest, explizitem PowerShell-Installer, getrenntem
  CUDA-Prozess und Peak-VRAM-Rückgabe. Keine Gewichte oder Downloads im Repo.
  Demucs-CPU-Rückfall in der vorhandenen lokalen Python-Umgebung; Gewichtsdownload
  über torch.hub wird im Fallback blockiert. Bestehende Demucs-API unverändert.
- Asynchrone SeparationJobs in den RT-Routen, gemeinsamer GPU-Manager, SHA-256-Cache,
  Ergebnis-Assets, WAV-Ausgabe und begrenzter atomarer PCM16-Mixexport.
  Jobstatus im bestehenden v1-Schema; Mehrspur-Ergebnis über eigene Detailadresse.
- Eigenständige UI für Songauswahl aus Shell, Start, Polling, Abbruch, Offline-Vorschau,
  A/B, Solo/Mute/Gain und Mixexport. Gemeinsame Shell gehört KETTE-43; der Einbau ist
  konkret in docs/realtime/hooks/WP25.md dokumentiert, noch nicht tatsächlich gemountet.
- Messpfad benchmarks/separation/product_job.py; bisheriger Qualitätsbericht aus WP08
  bleibt verwendbar.

## Abnahme und Belege

| Punkt | Implementierter Beleg | Status |
|---|---|---|
| 25.1 Dateijob, Fortschritt, Cancel, source/out_dir/Ergebnis-Pfadflucht, Fremddatei, Deadline | tests/realtime/test_file_jobs.py (nachgebauter Subprozess; test_success, test_cancel, test_paths, test_result_escape, test_unreported_file, test_timeout) | Testcode gepusht, nicht ausgeführt |
| 25.2 RoFormer-Fehler, Demucs-Rückfall und Cache-Treffer ohne neuen Worker | tests/realtime/test_separation_jobs.py (test_fallback, test_cache_assets_export); vorhandene test_stem_adapter.py | Testcode gepusht, nicht ausgeführt |
| 25.3 Bestands-Stems und CI | tests/test_stems.py nicht geändert; python -m unittest discover -s tests -v | nicht geprüft; CI-Nachweis fehlt |
| WP08 Modellabhängige Stem-Liste, Parameter/Revision, Abbruch und Cache | test_stem_adapter.py; test_separation_jobs.py (auch Negativfälle und v1-Schema); test_file_jobs.py | nicht geprüft |
| WP08 A/B, Solo/Mute/Gain, WAV und Job-API | tests/realtime/advanced_stems.test.mjs; tests/realtime/separation_jobs.test.mjs | nicht geprüft; tatsächlicher Shell-Mount offen |
| WP08 echtes Modell, Peak, Rekonstruktion, Leakage, Alignment und Hörprüfung | unten genannte Skripte | **nicht gemessen** |

Nachstellen (Python 3.11, Node 22):
    
    python -m unittest discover -s tests -v
    python -m unittest tests.realtime.test_file_jobs tests.realtime.test_separation_jobs -v
    node --test tests/realtime/separation_jobs.test.mjs tests/realtime/advanced_stems.test.mjs

Der letzte CI-Abruf vor der Übergabedokumentation für 3ada58fe332c2da96c81ee0e76be6c8c6953b6a5
ergab workflow_runs=[] und statuses=[]. Kein positiver oder negativer Testnachweis,
keine Joblogs verfügbar. Lokaler Git-Zugriff fehlgeschlagen:

    fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com

## Zielrechner – nicht gemessen

Explizite Installation, außerhalb des Repos; danach ausgegebenen Python-Pfad lokal in
.env setzen, SIRENS_RT_ENABLED=1, Dienst neu starten. Keine Gewichte ohne Schalter.

    powershell -File workers/separation/install.ps1 -ModelleLaden -Umgebung C:\SirensModels\separation
    python -m benchmarks.separation.product_job "Album/Song.wav" C:\SirensMessungen\roformer-01
    python -m benchmarks.result C:\SirensMessungen\roformer-01\result.json

Für einen Cache-Treffer dasselbe Original und einen neuen Ausgabeordner verwenden.
Der Produktjob misst einen Lauf einschließlich IPC und Polling, keine belastbare
Latenzverteilung. Bei Cache-Treffer keine Inferenzmesswerte. Für Leakage und Lag
zusätzlich samplegleich gemischte, geeignete lokale Referenzen:

    python -m benchmarks.separation.quality ORIGINAL.wav VOCALS.wav INSTRUMENTAL.wav REF_V.wav REF_I.wav EXTERNES_RESULTAT.json

Danach Mixer im Browser mit Ton prüfen; G3 und Hörqualität nicht behauptet.
Kein Audio einchecken.

## Versionen, Entscheidungen, Grenzen und Risiken

- MSST 1523206d12a521bdb20673726562524cf0f9635b (MIT); KimberleyJSN/MelBandRoformer
  Gewicht MIT laut Spike, Revision ac9b0614ab3cd7f77219e18ba494dfd93956c348,
  SHA-256 87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e.
  Torch/Torchaudio 2.7.1+cu128, weitere direkte Pins in requirements.lock;
  transitive Pins weiterhin offen. Demucs 4.0.0 (MIT; Gewichte/Lizenzen der
  Bestandsinstallation separat prüfen).
- RTX 5080 16 GiB; unbekannter Peak, als konservatives vorläufiges Lease-Budget
  8 GiB gewählt, kein Messwert. GPUManager-Reconcile und eventuelle Eviction
  auf Zielhardware prüfen. Worker-Peak misst allocated, nicht reserved.
- Aktuell nur PCM16/24-WAV, 44,1 kHz, Stereo, maximal 10 Minuten und 160 MiB Eingabe;
  kein Resampling, MP3/FLAC oder Streaming. Demucs-Fallback benötigt lokal
  vorhandene Demucs-Gewichte; ohne diese ehrlicher Fehler statt automatischem Bezug.
  Der neue SHA-256-Cache ist unabhängig vom alten Demucs-Cache. Framezahlprüfung
  belegt keine Phasen- oder Sampleausrichtung.
- Ein aktiver Job, 64 Jobdatensätze, 320 Assets und 32 Exporte pro Dienstlauf;
  Cache-/Exportquoten und Bereinigung über Dienstneustarts noch prüfen.
  Assets/Jobs leben im Speicher, Cache und Exporte bleiben persistent.
  Mehrere vollständige Spuren im Browser benötigen RAM. Fortschritt ist
  grob (Worker-Start und Abschluss), nicht chunkgenau.
- Technische Offline-Korrelation session_id=id im bestehenden v1-Jobformat,
  ohne echte Mock-Sitzung. Detailadresse getrennt, eingefrorene Schemata unverändert.
  Semantik dieser Korrelation und Integration in weitere RT-Verbraucher prüfen.
- Registry-Verfügbarkeit folgt lokal konfiguriertem Interpreter; Installation
  prüft CUDA, Pins und Gewicht, tatsächliche Modellprobe/Inferenz nicht nachgewiesen.
- Shell-Datei bewusst nicht geändert: KETTE-43 besitzt gemeinsame Dateien. WP25-Hook
  muss übernommen und Panic/Player-Lebenszyklus geprüft werden.
- Keine Änderungen an board.md, Register oder fremden Kettendateien als eigene
  Änderungen; Integrationszweig wurde mehrfach per Merge-Commit übernommen,
  ohne Force-Push.

## Übergabe

**Fertig:** oben genannte Backend-, Worker-, UI- und Messmodule, Tests und Hook
gepusht. Genau ein Ketten-PR #25 gegen integration/sirens-rt.
**Offen:** CI-Nachweis, tatsächlicher Shell-Einbau und gemeinsamer Player/Panic,
echte Installation und Produktjob/Hörprüfung, Abnahme der Offline-Job-Korrelation.
**Nächster Schritt:** Koordinator/KETTE-43 übernimmt WP25-Hook, CI für PR #25
ausführen und Fehler korrigieren, anschließend Zielrechner-Messpfad und WP08-
Qualitätsprüfung. Keine Freigabe für Live/Streaming oder DrumSep.
**Fehlerausgabe/Blockade:** lokales git ls-remote: Could not resolve host: github.com;
CI-Abfragen workflow_runs=[] / statuses=[]; keine Testlogs. Kein grüner Stand
behauptet. PR als ÜBERGABE auf Ready for review, nicht mergen ohne Abnahme.
**Rollback:** PR nicht mergen bzw. nur die eigenen AUFGABE-25-Änderungen revertieren;
RT-Schalter aus; lokale Worker-Umgebung und Cache/Exporte bei Bedarf separat
entfernen. Originalmusik unverändert.
