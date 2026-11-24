# AUFGABE-23 – Messpfade RAVE und AFTER

Stand: Übergabe, 24.11.2026. WP02, Depends-on KETTE-13 (gemergt). Gate G1 für beide nicht_gemessen; keine Produktfreigabe.

## Umsetzung und Abnahmebelege

| Abnahmepunkt | Umsetzung / Nachweis | Stand |
|---|---|---|
| 1: Dry-Run | python -m benchmarks.spikes.rave.messen --dry-run; python -m benchmarks.spikes.after.messen --dry-run; bestehender tests/test_spike_runner.py erfasst beide | Nicht ausgeführt; CI ausstehend |
| 1: Manifest | Beide weights.json mit Pflichtfeldern; RAVE LFS-Pointer exakt, AFTER unbekannte Werte null und Bezug gesperrt | RAVE belegt; AFTER unvollständig |
| 1: Kein Bezug ohne Schalter | install.ps1 / install.py, explizite Bestätigung; tests/realtime/test_spike_rave_after.py testet Netz- und Prozessfreiheit ohne Schalter sowie RAVE-Hash/Größe | Tests geschrieben, nicht ausgeführt |
| 1: Sicherer Loader | RAVE prüft gepinnten Hash und Größe unmittelbar vor TorchScript-Laden; AFTER nur registrierter vertrauenswürdiger lokaler Export mit Größe/Hash und konkreter Lizenz. Kein Checkpoint-Loader. Bestehender test_spike_weight_safety.py und neuer Mock-Test | Nicht ausgeführt; TorchScript bleibt ausführbarer Code |
| 2: PR-CI grün | GitHub-Workflow Tests: python -m unittest discover -s tests -v | Nicht bestätigt; Workflow- und Statusabfrage ergaben leere Listen, keine Fehlerlogs verfügbar |

RAVE: Windows-Wheel Torch 2.7.1+cu128, kein Training/Build nötig. Modell IIL, modifiziertes RAVE v1, kausal/Streaming, Revision 8471a1691f659ce52fcb2bb393afcc6f80187b17. CC BY-NC 4.0, 163881670 Bytes, SHA-256 02458214e23890d6818504319a5b9903eabfe87a524491f6524f453e7f3dbcf0. Quellen: https://huggingface.co/Intelligent-Instruments-Lab/rave-models und https://huggingface.co/Intelligent-Instruments-Lab/rave-models/commit/8471a1691f659ce52fcb2bb393afcc6f80187b17 ; Upstream https://github.com/acids-ircam/RAVE (CC BY-NC 4.0 laut Vorbericht). Abweichung: IIL-Gitarrenexport statt Raspberry-Variante, weil hierfür unveränderliche Metadaten vorliegen. HF kennzeichnet TorchScript als verdächtig; Quelle vor Ausführung prüfen. Blockmessung über synchronisierte Einzelblöcke und JSONL zusätzlich zum gemeinsamen Runner; kein Echtzeit-Pacing.

AFTER: Notebook am Commit 21298c907f469d6c7787c60dd38d46f98981b75c über GitHub gelesen; Code CC BY-NC 4.0 (LICENSE.md). Vollständiger lokaler v2-TorchScript-Export mit getrennten Struktur-/Timbre-Signalen, 10 Diffusionsschritten und Decoder; Lookahead statt Streaming. Kein Fallback auf festen Timbre-Vektor. Separate Gewichtslizenz, Dateiname, Bytezahl, Hash nicht belegt. Kein automatischer Gewichtsbezug; lokale Registrierung nach Herkunfts-/Lizenzprüfung und Hash. Quellen https://github.com/acids-ircam/AFTER und https://nubo.ircam.fr/index.php/s/8NFD5gWwbkT4G5P . Torch 2.7.1+cu128 für beide (https://download.pytorch.org/whl/cu128/torch/). Transitive Paketauflösung nicht vollständig vorgepinnt, lokale installed.lock wird nach Installation geschrieben. Python 3.11 für Inferenz, AFTER-Upstream-Export laut README Python 3.12.

## Nicht gemessen / Nachstellen

RTX 5080, CUDA, CPU, echte Inferenz, Installation auf Windows, VRAM, Hörprüfung und End-to-End-Latenz nicht gemessen. Keine Gewichte oder Musikdateien im Repo. Koordinatorbefehle in benchmarks/spikes/rave/BERICHT.md und benchmarks/spikes/after/BERICHT.md, aus der Übersicht verlinkt. Lokaler Testbefehl: python -m unittest discover -s tests -v. Vollständiger Checkout und lokaler Testlauf nicht durchgeführt; Änderungen direkt per GitHub-API gepusht.

## Übergabe

- Fertig: RAVE-Manifest, expliziter Installer, Block-Inferenz mit RTF, AFTER-Adapter nach Notebook und lokale Export-Registrierung, Offline-Tests, Nachstellbefehle.
- Offen: CI-Ergebnis, realer RAVE-Exportlauf, AFTER-Gewicht und separate Lizenz/Herkunft (inkl. konkreter Version, Größe, Hash), realer AFTER-Exportlauf; vollständige transitive Locks. Keine Freigabe für kommerzielle Nutzung.
- Nächster Schritt: RAVE zunächst CPU und dann CUDA nach Bericht messen; bei AFTER im offiziellen Share den vollständigen v2-Audio-to-Audio-Export samt Lizenz/Herkunft prüfen bzw. vertrauenswürdig selbst exportieren, registrieren und CPU/CUDA testen. CI am PR prüfen, ggf. Fehler beheben. Gate ausschließlich durch Koordinator.
- Fehlerausgabe / Blockade: Webabruf des offiziellen AFTER-Shares: "URL ... is not accessible via this tool." GitHub-Workflow-Abfrage für letzten Implementierungsstand: workflow_runs=[]; kombinierter Status: statuses=[]. Keine CI-Fehlerausgabe verfügbar. Kein grünes CI-Ergebnis behauptet.
- Rückbau: PR nicht mergen oder Kettencommits revertieren; beide install.ps1 -Entfernen, lokale Messresultate separat entfernen.
