# WP11 – Messung und Hörprüfung (nur Koordinator)

Kein G1 oder G3 durch Dry-Run, keine Netzarbeit in Tests. Windows, Repo-Root, Python 3.11, Torch 2.7.1+cu128 ausschließlich Wheels. Erst G1 messen und konkrete Herkunft/Lizenz des ausführbaren TorchScript-Exports prüfen. Keine Checkpoints oder pickle-basierten State-Dicts. Hash ist kein Nachweis der Sicherheit. RAVE: IIL Gitarrenmodell CC BY-NC 4.0 (Namensnennung), AFTER: separater Lizenznachweis für vollständigen v2-Export erforderlich.

    python -m benchmarks.neural_mutation.messen rave --dry-run
    python -m benchmarks.neural_mutation.messen after --dry-run

    .\workers\rave\install.ps1 -ModelleLaden
    .\.venv-spike-rave\Scripts\python.exe -m benchmarks.neural_mutation.messen rave --measure --device cuda --seconds 1800

    .\workers\after\install.ps1 -ModelleLaden -LokalerExport $export -Sha256 $sha -Gewichtslizenz $license
    .\.venv-spike-after\Scripts\python.exe -m benchmarks.neural_mutation.messen after --measure --device cuda

Optional zuerst mit --device cpu. RAVE misst drei Latent-/Morph-Presets und 30 Minuten Block-Deadlines (2048 Frames / 48 kHz). AFTER misst zwei unabhängige Timbres und Struktur-Guidance bei 44,1 kHz, jeweils 64 Codec-Frames. Kalt = Laden + erste Inferenz; warm = zweite Inferenz; AFTER lädt den zustandsbehafteten Export pro Job erneut. Ausgaben: benchmarks/results/local/wp11-*/result.json (benchmarks.result v1, gate=nicht_gemessen, cases, soak, torch_peak_reserved_mib), result.md und drei synthetische Hörproben. Kein User-Audio, keine Daten im Git.

Bei Streaming-Gate zusätzlich echte Audioausgabe, Caches/Impulsantwort (Context/Latency), Control-to-audio und Browser-Underruns bei tatsächlicher Rate und 30-minütigem Betrieb messen; der Block-Deadline-Test allein reicht nicht. Für jedes Modell drei Hörproben beurteilen, CPU/GPU-VRAM (gesamt und Prozess) erfassen, Abbruch und Rückkehr zu Dry prüfen. RAVE Mono-Wet und Stereo-Dry können phasenverschoben sein, keine Alignment-Zusage. Ausgaben und Gate getrennt bewerten. Erst Koordinator trägt G1/G3 ein und entscheidet Modus.

## Eigenes Training (nur Konzept, kein Code)

Separates Profil Training/Render mit exklusiver GPU-Lease; Live-/Neural-Worker zuvor entladen, VRAM-Budget und GPU-Temperatur überwachen. Keine automatische Datensammlung, nur eigene oder lizenzierte Audios, getrennte lokale Trainingsumgebung außerhalb des Dienstes. Code- und Gewichtslizenz vor Export prüfen; nur vertrauenswürdigen lokalen Export mit unabhängig erfasstem SHA-256 und dokumentierter Revision registrieren. Nicht kommerziell ohne gesonderte Lizenz. Kein Trainings-Job über HTTP, kein Training parallel zur Live-Performance. Neues Gate je Export, Rückbau durch Löschen der isolierten Umgebung.
