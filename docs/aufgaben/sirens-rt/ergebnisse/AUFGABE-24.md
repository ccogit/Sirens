# AUFGABE-24 – Messpfad Magenta RealTime

WP02, Depends-on AUFGABE-21. PR #21 gegen integration/sirens-rt, Branch extern/KETTE-16.

## Umsetzung

MRT2 Small (230M), JAX unter Ubuntu 24.04/WSL2, Python 3.12 nur in isoliertem Spike; Hauptprozess unverändert. Offizielle Paketprovenienz magenta-rt 2.0.3, Commit 694a545e4ba0b88bf1150137b129582166d3e07f, Apache-2.0; JAX 0.10.1 mit CUDA12-Plugin/PJRT 0.10.1. Gewichtsrevision 7803d987f43f7142cfc7d68ba3361c5f83023931, CC-BY-4.0 mit Nutzungsbedingungen. Exakte Größen und SHA-256 aus LFS-Pointern, URLs in weights.json. Kein HF-Zugang auf öffentlicher Modellseite ersichtlich. Quellen und vollständige Aufrufkette in benchmarks/spikes/magenta-realtime/BERICHT.md.

## Abnahme

| Punkt | Beleg | Status |
|---|---|---|
| Dry-Run | python -m benchmarks.spikes.magenta-realtime.messen --dry-run; test_magenta_spike.py::test_dry_run | Implementiert, Ausführung noch nicht bestätigt |
| Manifest | weights.json; sechs offizielle LFS-Größen und SHA-256, Lizenz und unveränderliche Download-URL; test_manifest_and_no_download_without_flag | Quellen geprüft; tatsächlicher Bezug nicht durchgeführt |
| Kein Bezug ohne Schalter | install.ps1 und install.py; test_manifest_and_no_download_without_flag, test_download_rejects_corruption_and_reuses_valid | Implementiert; Tests noch nicht bestätigt |
| Sichere Loader | SHA-256/Größe vor Inferenz aller benötigten Dateien; Upstream JAX safetensors.flax.load_file, LiteRT/SentencePiece. test_spike_weight_safety.py unverändert | Quellprüfung, CI noch nicht bestätigt |
| Echte Inferenz | MagentaRT2Jax, Waveform-Fixture, MusicCoCa-Stilembedding, generate(frames=1, state=...), test_block_continues_state | API am gepinnten Upstream gelesen, tatsächlicher Modelllauf nicht gemessen |
| CI | python -m unittest discover -s tests -v; GitHub Actions PR #21 | Nicht bestätigt |

Messformat: gemeinsamer runner-Parser und Sampler, common und result. Der Torch-spezifische runner.run wird im Dry-Run, nicht im JAX-Echtlauf benutzt. RTF jedes 40-ms-Blocks, kalte Lade/JIT/Embedding/Erstausgabezeiten, warme Perzentile, VRAM-Sampling, lokale Hörproben. Keine End-to-End-Audiolatenz und kein Gate. Zielhardware Windows 11 / RTX 5080 16 GB VRAM: **nicht gemessen**. Messaufrufe siehe BERICHT.md.

## Abweichungen und Risiken

- WSL2/JAX statt nativer Windows- oder Torch-Umgebung; CPU und CUDA12 zur Messung auswählbar. Upstream empfiehlt JAX auf Linux als Offline-Pfad. Keine Echtzeitbehauptung.
- requirements.lock enthält Versionsconstraints aus Upstream uv.lock. CUDA-Laufzeit-Transitive außerhalb dieses Locks nicht vollständig fixiert; keine reproduzierbare Wheel-Auflösung nachgewiesen. Kein C/C++-Build zugelassen.
- Nur Small und erforderliche Audio-Embedding-Ressourcen, kein Base, kein MLX, kein Mapper. Audio-Embedding aus Fixtures, keine lokalen Benutzertracks.
- Kein kompletter lokaler Checkout: DNS-Zugriff der Ausführungsumgebung auf github.com fehlgeschlagen. Commits über GitHub-API auf den Remote-Branch geschrieben. Tests lokal nicht gelaufen.
- Rückbau: PR nicht mergen bzw. Kettencommits revertieren; eigene WSL-Umgebung mit install.ps1 -Entfernen entfernen. Keine Produktintegration.

## Übergabe

Fertig: Quellenpins, Gewichtsmanifest, expliziter Installer, JAX-Inferenzpfad, netzfreie Regressionstests, Bericht, Übersichtszeile. Keine Änderungen am Register, Board oder Produktcode.

Offen: CI grün bestätigen und ggf. Fehler beheben; WSL-Wheel-Auflösung/Installation, tatsächliche Inferenz und RTX-5080-Messung durch Koordinator. CUDA-Transitive nach erfolgreicher Auflösung in Lock übernehmen. Branchvergleich vor diesem Dokumentationscommit: ahead 9, behind 0.

Nächster Schritt: PR-Checks prüfen, dann kopierbare Befehle aus BERICHT.md auf dem Zielrechner ausführen. Fehlerausgabe lokaler Checkout: `fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`. CI-Abfragen am letzten Code-/Dokustand c7915b6: workflow_runs=[] und statuses=[]; kein CI-Fehlerlog abrufbar, damit kein Grün-Nachweis. Gate bleibt nicht_gemessen.
