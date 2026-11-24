# Betrieb, Fehlersuche und Release-Runbook

1. Vor Start Git-Stand, Python, Node, NVIDIA-Treiber und freie Ressourcen
   prüfen. Keine Secrets im Protokoll. Installationsanleitung befolgen.
2. Mit SIRENS_RT_ENABLED=aus und ohne Worker starten: start.ps1 -Open.
   Health (/api/health), Auftragsverwaltung, Katalog, Mastering, Live Lab,
   Auto-DJ und Bestand anhand synthetischer Testdaten prüfen. RT-API muss
   gesperrt sein. Demucs-Studio nur mit seiner getrennten Bestandsumgebung.
3. Erst bei freigegebenem Testbetrieb RT einschalten. Fehlende Modelle
   müssen als nicht verfügbar erscheinen. Keine Downloads beim Öffnen.
4. Bei Aussetzern Dry/Bypass, Stop/Panic; Sitzung schließen. Eigene
   Worker/Sidecars prüfen, nicht fremde GPU-Prozesse beenden.
5. Bei Startfehler %TEMP%/sirens/dienst.err.log lokal lesen; vor Weitergabe
   Pfade, Zugangsdaten und private Daten entfernen. Bei CUDA-Fehler
   nvidia-smi und isolierte Worker-Umgebung prüfen; kein globales pip.
   Bei OOM Modell stoppen, Ressourcen freigeben, kleineres freigegebenes
   Profil verwenden. Bei Hashfehler nicht umgehen, Quelle und Pin prüfen.
   Bei DEMON fehlendem uv.lock automatische Installation nicht erzwingen;
   bei SAM 403 Zugang/Lizenz klären, keine Umgehung.
6. Für Rückfall Dienst stoppen, Flag aus, RT-Pfade bei Bedarf entfernen,
   Legacy neu starten. Keine Originale oder Sitzungsdaten löschen.

## Abnahme und RC

    python -m unittest discover -s tests -v
    python -m benchmarks.rollout --worker rave --dry-run --out C:\TEMP\rt-dry.json
    python -m benchmarks.result C:\TEMP\rt-dry.json

Für einen frischen Installationsversuch mit freigegebenen Quellen:
    
    python -m benchmarks.rollout --worker rave --install --disk-bytes $disk --vram-mib $vram --accept-incomplete-locks --out C:\TEMP\rt-install.json
    python -m benchmarks.result C:\TEMP\rt-install.json

Die Werte $disk und $vram vorab nach Installationsanleitung festlegen.
Der Schalter für unvollständige Locks ist nur ein Entwicklungsversuch.
Für AFTER/SAM sind die zusätzlichen lokalen Eingaben am direkten
PowerShell-Einstieg erforderlich; DEMON und Magenta bleiben dort blockiert.
Installationsbericht hält Exitcode und Baseline fest; keine Modell- oder
Audio-Latenzen, keine automatische Gate-Entscheidung. Installationslauf,
Legacy-Sichtprüfung und Deinstallation zusätzlich protokollieren.
G4-Soak gemäß [abnahme.md](abnahme.md); G4 derzeit **nicht gemessen**.
CI, vollständige Locks, erfolgreiche frische Installation, G3/G4,
Lizenzprüfung und Eigentümerfreigabe vor RC. Kein Tag/Release/Merge
nach main durch WP20. Bei negativem Modell-Gate betreffende Funktion
gesperrt lassen; bei Kern-/Sicherheits-/Bestandsfehler kein RC.
