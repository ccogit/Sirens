# AUFGABE-15 – Generative Companion (WP15)

Depends-on: WP06, WP10 und WP24. PR #30, extern/KETTE-36 gegen integration/sirens-rt.
G1 Magenta RealTime 2 ist noch nicht gemessen; keine Freigabe, kein Streaming und keine Beatbindung behauptet.

## Umsetzung

- workers/magenta/: v1-Manifest (available=false, auch mit gesetztem Interpreter), zustandsbehafteter
  Adapter mit lokaler Stereo-Stilreferenz, Gain, Bypass, Warmup, Cancel/Epoch, Unload und begrenzten PCM-Blöcken.
  Persistenter IPC-v1-Worker mit Heartbeat, fester WSL2-Startkette und Modell-Backend ausschließlich im isolierten
  Prozess. Kein Modellimport in sirens/.
- Eigene WSL2-Umgebung ~/.venv-worker-magenta. Expliziter Installer mit Wheel-only und Lizenzbestätigung,
  Hash- und Größenprüfung aller sechs Ressourcen. Kein Download bei normalem Start, Probe oder Tests.
  Pins und Gewichtsmanifest aus WP24 übernommen.
- Hook docs/realtime/hooks/WP15.md für KETTE-43: separater AudioCore-Eingang, gemeinsamer Startframe,
  Pegel, Bypass, Stop, lokale Stilreferenz und vorgeschlagenes MIDI-Mapping, GPU-Lease, Cache- und Sicherheitsregeln.
  Gemeinsame Dateien, Board und Register unverändert.
- benchmarks/companion/messen.py: 600 Sekunden erzeugtes Audio, inkrementelles WAV außerhalb der Musikquelle,
  Referenzwechsel nach halber Dauer, Kalt-/Warmzeiten, RTF, GPU-Sampling, Stop-Prüfung, result.json und result.md.
  Kein Modelllauf ohne ausdrückliches --echt.

## Abnahme

| Punkt | Beleg | Status |
|---|---|---|
| Lebenszyklus und Zustandsfortsetzung | tests/realtime/test_magenta_companion.py: test_lifecycle_reference_and_gain, test_warmup_resets_state, test_backend_model_api, test_ipc_control_lifecycle | Implementiert, CI am Gesamtstand nicht bestätigt |
| Stop und Bypass | test_cancel_during_generation, test_bypass_and_unload; Hook für Stop und Gain=0 im AudioCore | Modellnachbau-Tests vorhanden; Browser-/WSL-Stop nicht gemessen |
| Regler | test_lifecycle_reference_and_gain (Pegel, Referenzwechsel), test_invalid_inputs | Tests vorhanden; Live-MIDI/Style-Mapping im Browser nur Hook, Text-API offen |
| Standardmäßig deaktiviert | test_registry_gate_disabled; Manifest available=false | Keine Aktivierung durch Installation |
| Installer/keine Gewichte im Test | test_installer_without_opt_in, test_backend_model_api | Expliziter Bezug; nur Modellnachbau im Test |
| 10-Minuten-Begleitspur | benchmarks/companion/messen.py; test_benchmark_short_mock (1 s, temporäre WAV, Schema, Stop) | Echte 600 s, Ressourcen und Hörprüfung: **nicht gemessen** |
| Gesamtsuite | python -m unittest discover -s tests -v | erster Commit f217c91: GitHub Actions Tests #266 erfolgreich; Gesamtstand noch nicht bestätigt |
| Board | gemäß Kettenregeln nur durch Koordinator | nicht verändert |

## Versionen, Lizenzen, Hardware

Magenta-rt 2.0.3, Code-Commit 694a545e4ba0b88bf1150137b129582166d3e07f, Apache-2.0.
MRT2 Small (230M), Gewichtsrevision 7803d987f43f7142cfc7d68ba3361c5f83023931,
CC-BY-4.0 und Nutzungsbedingungen (Rechte Dritter beachten); genaue Dateien/Hashes in weights.json.
Ubuntu 24.04/WSL2, Python 3.12 nur dort, JAX/JAXlib 0.10.1, CUDA12-Plugin/PJRT 0.10.1,
safetensors 0.7.0. Kein Torch erforderlich; sicherer Loader laut WP24 safetensors.flax.load_file,
MusicCoCa mit LiteRT/SentencePiece. Nur Wheels; CUDA-Laufzeit-Transitive noch nicht vollständig gepinnt.
Zielrechner Windows 11, RTX 5080 16 GB; VRAM, Blackwell-Kompatibilität, Installierbarkeit nicht gemessen.
Etwa 2 GB Modellgewichte plus separate Umgebung und lokale Messausgaben.

## Nachstellen (Koordinator)

PowerShell im Repo-Root:
    .\workers\magenta\install.ps1
    .\workers\magenta\install.ps1 -ModelleLaden
    wsl --cd (Get-Location).Path

WSL im Repo-Root:
    $HOME/.venv-worker-magenta/bin/python -m benchmarks.companion.messen --echt --seconds 600

Ergebnis unter benchmarks/results/local/companion-*/result.json, result.md und companion.wav.
Validierung: python -m benchmarks.result <result.json>. Ohne --echt nur Hinweis, keine Modellinferenz.
Browser-Hörprüfung und tatsächlicher GPU-/WSL-Prozessbaum-Stop gemäß WP15-Hook nach Einbau.
Keine Messwerte oder G1-Freigabe erfunden. CI: python -m unittest discover -s tests -v (Python 3.11, Node 22).

## Abweichungen / Risiken / Rückbau

- Nur geprüfter WP24-Audiokonditionierungspfad implementiert; native Text- und MIDI-Konditionierung
  nicht belegt. MIDI-Mapping auf Gain/Referenzwahl nur als Hook, kein fertiger Browser-/HTTP-Workflow.
  Frozen Supervisor erlaubt bei process nur PCM, bei load numerische Controls; Text benötigt geprüfte
  Upstream-API und ggf. ADR. Kein Beat- oder Echtzeitversprechen.
- WSL-Prozessbaum und binäres IPC über Windows/WSL, JAX-Freigabe bei Stop, AudioCore-Spur und hörbare
  Reglerwirkung auf Zielsystem nicht geprüft. Nicht aktivieren, bevor dies und G1 belegt sind.
- Installer-Pins stammen aus WP24, die CUDA-Laufzeit-Auflösung ist nicht vollständig reproduzierbar.
  Keine Wheel-Installation oder echte Inferenz durchgeführt. Offline-Netzfrei-Nachweis am Zielsystem offen.
- Kein vollständiger lokaler Checkout: DNS der Arbeitsumgebung löst github.com nicht auf. GitHub-API
  für alle Commits genutzt. Keine lokalen Testergebnisse. Rückbau: PR nicht mergen bzw. Kettencommits
  revertieren; eigene WSL-Umgebung mit install.ps1 -Entfernen löschen. Lokale Messergebnisse separat entfernen.

## Übergabe

Fertig: Manifest deaktiviert, WSL-Worker, Adapter, Installer/Lock/Hashmanifest, Modellnachbau-Tests,
Langlaufskript, Hook. Alle Änderungen auf dem zugewiesenen Branch; keine gemeinsamen Dateien geändert.

Offen: CI für Gesamtstand abwarten und ggf. Fehler beheben; Text-/MIDI-API bzw. Mapping vollständig
umsetzen/prüfen, WP15-Hook in KETTE-43 integrieren, WSL-Prozessbaum und Installer auf Zielrechner prüfen,
G1 und 600 Sekunden echte Begleitspur mit Hörprüfung durch Koordinator messen. Capability bleibt aus.

Nächster Schritt: PR-Checks für den letzten Stand prüfen; anschließend bei bestandenem G1 die dokumentierte
WSL-Messung und Browserintegration ausführen. Branchvergleich vor Dokumentationscommit: ahead 15, behind 0.
Fehlerausgabe lokaler Checkout: fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com.
CI-Abfrage für c47ccfacca4d34ab7ebf0be96dedd16f66b85ad2: workflow_runs=[] und statuses=[].
Kein Fehlerlog vorhanden, aber auch kein Grün-Nachweis für diesen Stand. Früherer Lauf
https://github.com/ccogit/Sirens/actions/runs/45461263542 erfolgreich, betrifft nur den ersten Commit.
