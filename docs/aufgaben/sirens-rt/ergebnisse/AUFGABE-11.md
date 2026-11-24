# AUFGABE-11 / WP11 – Neural Mutation

Depends-on WP06, WP23. G1 RAVE und AFTER nicht gemessen. Beide Kandidaten sind standardmäßig gesperrt, keine Downloads beim Start, keine Modellgewichte im Repo. Alle Änderungen auf extern/KETTE-34; PR #29 gegen integration/sirens-rt. Kein Register, Board oder gemeinsame Datei geändert.

## Umsetzung und Abnahme

1. Worker/Adapter: workers/rave und workers/after; isolierte WP23-Umgebungen, Install-Wrapper, Lockfile, pending-Manifest mit Descriptor (kein Streaming-Label). RAVE: 16 Latent-Offsets, Morph zwischen Original und verändertem Latent, Wet/Dry und Seed; AFTER: unabhängige Struktur-/Timbre-Referenzen, Guidance, Schritte, Wet/Dry und Seed. IPC v1 mit Heartbeat, Abbruch, begrenzten Audio-Blöcken. AFTER muss für zwei volle Referenzen die dokumentierte private Sequenz nutzen. Tests tests/realtime/test_neural_mutation.py: Lebenszyklus, Preset-Reproduzierbarkeit, separate Referenzen, Dry, fehlende Gewichte, gesperrter IPC-Probe/Load. tests/realtime/neural_mutation.test.mjs: deterministischer Random-Walk mit echtem WP10 BeatGrid, Tempoänderung und Seek. Noch keine echte Modellinferenz im Test.
2. Fehlende Gewichte: Adapter meldet Unavailable; Worker mappt auf IPC error unavailable. Realer Ladepfad wird im Negativtest mit temporärem leeren venv geprüft. Kein automatischer Download. RAVE nur nach expliziter Installer-Vertrauensbestätigung, fester Größe und Hash; AFTER nur registrierter lokaler Export samt Hash/Größe/Lizenz.
3. Zielrechner/Hören/Latenz/VRAM/Streaming: **nicht gemessen**. benchmarks/neural_mutation/messen.py mit drei Presets pro Modell, Kalt-/Warm-Latenz, synthetischen Hörproben, RAVE 1800 s Block-Deadline-Simulation; Ausgabe result.json und result.md nach benchmarks/result.py. Aufrufe und Trainingskonzept in benchmarks/neural_mutation/README.md; Dry-Run-Test test_neural_mutation_benchmark.py. Browser-/Audio-Device-Underruns und Control-to-audio separat nach Integration messen. Kein G1/G3 vorweggenommen.
4. CI: vollständiger Checkout lokal scheiterte mit fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com. Erster CI-Lauf (nur Doku) 45461240050 grün. Zweiter Lauf 45461475244: 171 Tests, 3 Fehler, 4 Skips, siehe Übergabe. Pending-Manifeste als Korrektur im Folgecommit 69658db; CI 45461719063 erfolgreich (https://github.com/ccogit/Sirens/actions/runs/45461719063). Abschließende Messskript-/Dokumentationsänderungen und deren Tests benötigen den finalen CI-Lauf. Board wird gemäß KETTEN.md ausschließlich vom Koordinator gepflegt.

## Versionen, Lizenz, Hardware

RAVE: acids-ircam/RAVE @ 7280bd5c11890b2043c5591f8da0ea5f4d5bf647 (Code CC-BY-NC-4.0), tatsächlich gepinnter IIL kausaler modifizierter v1-Gitarrenexport, Intelligent-Instruments-Lab/rave-models @ 8471a1691f659ce52fcb2bb393afcc6f80187b17, 163881670 Bytes, SHA-256 02458214e23890d6818504319a5b9903eabfe87a524491f6524f453e7f3dbcf0, Gewicht CC-BY-NC-4.0, Namensnennung IIL, DOI 10.57967/hf/1235. Native Rate 48000, Block 2048, 16 Latents. TorchScript ausführbar; kein allgemeiner Checkpoint-Loader.

AFTER: acids-ircam/AFTER v2 @ 21298c907f469d6c7787c60dd38d46f98981b75c, Code CC-BY-NC-4.0. Vollständiger Audio-to-Audio-Export (nicht Codec allein); Gewichtslizenz/Hash lokal zu bestätigen, Share in WP23 nicht zugänglich. Native Rate 44100, 64 Latentframes, Export ae_ratio bestimmt Kontext. Kein automatischer Bezug. Kein kommerzieller Einsatz ohne gesonderte Lizenz.

Beide: Torch 2.7.1+cu128 aus Wheel-Index, Python 3.11; isolierte vorhandene Spike-venvs, transitive Pins beim Install in installed.lock erfasst, nicht vollständig vorab gelockt. RTX 5080 16 GB Ziel, tatsächlicher Bedarf unbekannt; CUDA-Kompatibilität und Audioform erst mit freigegebenem Export prüfen. Keine Torch-/Modellimports in sirens/.

## Abweichungen / Risiken / Rückbau

Pending-Manifeste statt sofortiger Registrierung, weil bestehende CI bei deaktivierten realen Capabilities drei Altannahmen verletzt. Kein Eingriff in fremde Tests oder gemeinsame Registry. Hook WP11 beschreibt Registrierung, Gate-Freigabe, UI, sichere Quellauflösung, Supervisor-Anbindung, private AFTER-Sequenz und dynamischen RAVE-Regleranschluss. Bis dahin sind die UI-Kacheln noch nicht produktiv angeschlossen. RAVE-Walk berechnet exakte Takt-Ereignisse; Export ist blockgebunden und der aktuelle Supervisor hat keine dynamischen realen process-controls. Die zeitgenaue tatsächliche Anwendung im Audio ist daher offen. Keine Streaming-Freigabe. Wet/Dry-Latenzausgleich offen, AFTER-Speicher und Ladezeit pro Job unbekannt. Referenzjobs und Audio-Hörprüfung nach G1/G3.

Rückbau: pending lassen bzw. available=false, Worker schließen, Env-Einträge entfernen, workers/{rave,after}/install.ps1 -Entfernen (löscht jeweilige gemeinsame Spike-Umgebung), lokale Benchmarks separat löschen. Keine Quellen überschrieben.

## Übergabe

Fertig: Worker-Grundgerüst, Adapter, abgesicherter lokaler Ladepfad, Descriptor, Install-Wrapper, Lockfiles, Seed/Presets/Wet/Dry, BeatGrid-Walk, Tests, Messskript und dokumentierter Einbau. Offen: abschließende CI auf aktuellem Commit prüfen, G1/Hörmessung, Produktverdrahtung und dynamische RAVE-Regler sowie reale samplegenaue Takt-Anwendung; AFTER-Gewichtslizenz und Export prüfen. Nächster Schritt: CI auf aktuellem Commit kontrollieren, Hook mit KETTE-43 umsetzen, Gate messen, erst dann je Modell freigeben.

Fehlerausgabe CI 45461475244: test_gpu_routes.GPURoutes.test_registry: AssertionError: False is not true (Mock nicht an Index 0); test_rt_contracts.HTTP.test_switch_and_security: capabilities-Liste nicht leer; test_worker_supervisor.Workers.test_oom_and_rejection: Listen nicht gleich [] (zwei deaktivierte Deskriptoren). Korrektur: manifest.pending.json, keine vorzeitige Registrierung. Lokaler Checkout: Could not resolve host: github.com. Keine erfundenen Messwerte.
