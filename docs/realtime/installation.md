# Installation und Rückbau (WP20)

**Vorläufiger Rollout, keine Release-Freigabe. G4: nicht gemessen.**
Windows 11, Python 3.11, Node 22 (Tests), Git, NVIDIA-Treiber, FFmpeg wie im Bestand.
Hauptdienst bleibt Standardbibliothek. Keine globale pip-Installation, keine
Modellgewichte im Git, kein Bezug beim Dienststart. Lizenzmatrix siehe
[lizenzen.md](lizenzen.md).

## Vor dem Versuch

Separaten frischen Checkout und synthetischen Musikordner verwenden. Dienst
über Stop/Panic und anschließend start.ps1 -Stop beenden, eigene Worker im
Prozessmanager kontrollieren. In .env SIRENS_RT_ENABLED=aus und
SIRENS_RT_AUTODETECT=aus setzen; gleichnamige Prozessvariablen haben Vorrang.
Nie den echten Musikordner oder bestehende Worker-Umgebungen als Testziel
benutzen. Keine Modellpfade aus HTTP übernehmen.

Im Repo-Wurzelverzeichnis:

    .\scripts\rt-install.ps1 -DryRun
    .\scripts\rt-install.ps1 -Worker rave
    python -m unittest discover -s tests -v

DryRun gibt alle Ziele und Sperren aus, ohne sie anzulegen oder Programme
aufzurufen. Ohne Schalter nur Diagnose: Python, nvidia-smi (Treiber, maximale
CUDA-Treiberversion, freier/gesamter VRAM), freier Speicher auf Zielvolumes.
Das ersetzt keinen CUDA-Inferenztest. GPU 0 muss die vorgesehene GPU sein.

## Opt-in je Worker

Die vollständigen transitiven Wheel-Hash-Locks fehlen für die meisten
Worker. Deshalb ist das kein reproduzierbar freigegebener Paket-Rollout.
Die vorhandenen direkten Pins und Gewichts-Hashes bleiben verbindlich;
keine Hashes raten. Der normale Installationsversuch verweigert unvollständige
Locks. Für einen expliziten Entwicklungsversuch (nicht RC-Freigabe) kann der
Koordinator nach Quellen-/Lizenzprüfung die Sperre gezielt übergehen:

    .\scripts\rt-install.ps1 -Worker rave -ModelleLaden -MinFreeDiskBytes $disk -MinFreeVramMiB $vram -UnvollstaendigeLocksAkzeptieren

$disk und $vram vorher anhand der geprüften Download-/Installationsgröße
inklusive Cache/Reserve und GPU-Bedarf des gewählten Modells setzen (Bytes bzw.
MiB). Keine pauschalen ungemessenen Mindestwerte. Erst danach explizit mit
ja bestätigen. Die delegierten Installer können weitere Zustimmung verlangen.
Nicht parallel installieren oder Ordner umbenennen. Bei Abbruch bleibt das
Feature aus; keine teilweise installierte Umgebung konfigurieren.

| Worker | Pfad / Besonderheit |
|---|---|
| RAVE | .venv-spike-rave; nur nichtkommerziell, TorchScript nur aus geprüfter Quelle |
| AFTER | .venv-spike-after; zusätzlich -LokalerExport, -Sha256, -Gewichtslizenz; keine G1-Freigabe |
| Separation | %LOCALAPPDATA%/Sirens/rt-rollout-separation; nur RoFormer, nicht DrumSep |
| Stable Audio | %LOCALAPPDATA%/Sirens/rt-rollout-stable-audio; HF-Lizenz und lokaler Login, Cache explizit setzen |
| SAM Audio | .venv-sam-audio; -Wheelhouse, -GepruefterLock und -Receipt, ausschließlich lokaler geprüfter Bezug, G1 gesperrt |
| DEMON | automatischer Rollout gesperrt: fehlender Upstream uv.lock, dokumentierter manueller Messpfad in G1-Bericht ist kein vollständiger Hash-Lock |
| Magenta | separat WSL2 mit Python 3.12, Speicher/Dateieigentum prüfen; workers/magenta/install.ps1 -ModelleLaden erst nach Prüfung; keine G1-Freigabe |
| Mock | kein Installer; nur lokale Entwicklung, kein KI-Modell |

Nach erfolgreicher Prüfung nur die vom jeweiligen Installer ausgegebenen
SIRENS_RT_*_PYTHON- und Cache-/Receipt-Pfade in die lokale .env übernehmen.
G1 allein reicht nicht für Produktfreigabe. Erst nach G3/G4 und Freigabe
SIRENS_RT_ENABLED=an setzen. Mock aus lassen. Bei fehlender Fähigkeit nicht
durch Umbenennen eines Manifests erzwingen.

## Rückbau

Sitzung schließen, Dienst beenden, eigene Worker kontrollieren. Flag in
.env und Prozessumgebung ausschalten; Legacy-Dienst neu starten, ohne
Worker-Konfiguration. Vor einer Deinstallation wieder stoppen.

    .\scripts\rt-install.ps1 -Worker rave -Entfernen -DryRun
    .\scripts\rt-install.ps1 -Worker rave -Entfernen

Nur fest zugeordnete Ordner mit passender Rollout-Markierung werden gelöscht;
Bestandsordner, Symlinks/Junctions und deren Ziele werden nicht übernommen.
Magenta separat: nach Prüfung des eigenen WSL-Ordners
workers/magenta/install.ps1 -Entfernen. Keine fremden HF-Caches,
Musikdateien, Sitzungen oder Bestandsumgebungen löschen. Lokale veraltete
RT-Interpreter-/Cache-Einträge aus .env entfernen. Keine Secrets sichern
oder in Tickets kopieren. Rollback der Codeänderungen nur über WP20-Revert.
