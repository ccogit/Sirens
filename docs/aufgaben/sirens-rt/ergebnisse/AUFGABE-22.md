# AUFGABE-22 – DEMON

WP02; Depends-on: AUFGABE-21 (gemergt). Gate G1: nicht gemessen.

## Umsetzung und Abnahme

- Gepinnter DEMON-Code 96acc905204d54bfd3055084ca8e9df8a6d9a33f (AGPL-3.0-or-later, MIT-Anteile) und ACE-Step 1.5 Turbo HF-Revision 19671f406d603126926c1b7e2adc169acbcade22 (MIT). Quellen und kopierbare Befehle: benchmarks/spikes/demon/BERICHT.md.
- Abnahme 1: neuer Dry-Run über runner.py, Manifest-Pflichtfelder, Download-Sperre, SHA-256-Prüfung und Fehlerbereinigung in tests/realtime/test_demon_spike.py. Upstream ModelContext verwendet vendierte DiT-Klasse sowie weights_only=True für silence_latent.pt; zusätzlicher Torch-Sicherheitsmodus. Statischer Bestandstest bleibt unverändert. Exakte Bytezahlen und nicht veröffentlichte Hashes werden lokal ermittelt. Lokale Tests nicht ausgeführt (kein vollständiger Checkout); CI ist maßgeblich.
- Abnahme 2: CI des vorherigen Commits c530ca9 (Run 45457122498) bei Abruf in_progress; endgültiger CI-Status nicht belegt.
- Hardware: RTX 5080, 16 GB, Windows 11, Python 3.11; Eager-2B-Turbo mit Textencoder-Offload, CUDA 12.8, Torch 2.9.1. Echte Inferenz und VRAM nicht gemessen, kein Gate. RTF je fertig dekodiertem Fenster über Runner. Kontrollsprung im Denoise, aber keine gesonderte Reaktionszeitmessung und keine kontinuierliche Audioausgabe.
- Abweichungen: volle Paketpins und Windows-Wheel-Kompatibilität fehlen; keine zweite Modellvariante außer 2B-Turbo (statt XL); keine TensorRT-Messung. Keine echte Installationsprobe; keine Freigabe.
- Rückbau: nur Spike-Dateien/Tests/README-Zeile/Ergebnisdatei; isolierte Umgebung per install.ps1 -Entfernen löschen.

## Übergabe

**Fertig:** Manifest mit gepinnter Quelle und veröffentlichten Gewichtshashes, bestätigungspflichtiger Installer, lokaler Session-Adapter, Dry-Run, Offline-Tests und Ablauf. Kein Netz im Dry-Run.

**Offen:** vollständiger transitiver Lock und Windows-Wheels, echte Inferenz, exakte Control-to-audio-Messung, ggf. TRT oder SA3-Alternative. Keine CI-Grünbestätigung.

**Nächster Schritt:** Upstream-Checkout am Zielrechner prüfen, uv.lock falls vorhanden mit uv sync --locked --no-build prüfen; fehlt er, minimalen Inferenz-Lock mit CUDA-Wheels erstellen. Anschließend kopierbare Befehle im Bericht ausführen, Fehler korrigieren und erst nach Messung Gate entscheiden.

**Fehlerausgabe:** GitHub-Dateiabruf des gepinnten uv.lock: NOT_FOUND / HTTP 404; Webabruf: DisabledError. Das ist kein Beweis, dass die Datei im Checkout fehlt. Installer bricht bei fehlendem Lock explizit ab: „Upstream uv.lock fehlt; Paketpins vervollständigen, siehe Bericht“. Keine lokale Inferenz-Fehlerausgabe, da nicht ausgeführt.
