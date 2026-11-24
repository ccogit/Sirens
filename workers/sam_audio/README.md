# SAM Audio small – Offline-Worker (gesperrt)

Kein automatischer Bezug. G1 ist nicht gemessen. Code-Pin und bekannte Gewichtsmetadaten:
`benchmarks/spikes/sam-audio/BERICHT.md` und `weights.json`. Die bekannte Hashliste ist unvollständig;
kein freigegebener Lock für die vollständige Installation.

Der Koordinator muss den Code am dokumentierten Pin samt Git-Abhängigkeiten auditieren, insbesondere
die Konstruktoren für T5, optionale Ranker und Span-Prädiktoren. Diese deaktivieren bzw. auf lokale
geprüfte Safetensors umstellen; keine Fremd-Pickle-Dateien. SAM checkpoint.pt nur weights_only=True.
Alle transitiven Wheels und Modellartefakte einschließlich T5 und Tokenizer lokal bereitstellen,
Lizenz prüfen, ausgehenden Netzwerkverkehr im Workerprozess am Zielrechner blockieren. Offline-Flags
allein garantieren keine Netzisolation für beliebigen Drittcode.

Lokaler Installations-Lock: pro Zeile Paket==Version und ein oder mehrere --hash=sha256:<64 Hexzeichen>.
Keine URLs, Quellpakete oder Includes. Geprüfte Wheels außerhalb des Repos. Torch/Torchaudio
2.7.1+cu128 und Torchvision 0.22.1+cu128; deren Kompatibilität mit SAM noch nicht gemessen.
`requirements.lock` enthält nur bereits bekannte Pins, nicht den vollständigen Hash-Lock.

Receipt (außerhalb Repo; erst nach Audit erstellen, keine echten Pfade/Hashes committen):
```json
{
  "code_pin": "bb4c6999d2677c7402360e426afc01ddfad6dce0",
  "offline_audited": true,
  "snapshot": "<absoluter lokaler vollständiger Snapshot>",
  "files": {
    "config.json": "<SHA-256>",
    "checkpoint.pt": "<SHA-256>"
  }
}
```
Die Liste muss sämtliche Dateien der Snapshot-Closure enthalten, auch lokale T5-Dateien;
keine Symlinks. Receipt ist eine lokale Betreiberbestätigung, kein Nachweis eines bereits
bestandenen Gates. Auch den Code/Wheel-Pin und die Gewichtrevision separat dokumentieren.

```powershell
.\workers\sam_audio\install.ps1
.\workers\sam_audio\install.ps1 -Installieren -Wheelhouse <lokal> -GepruefterLock <lokal> -Receipt <lokal>
$env:SIRENS_RT_SAM_AUDIO_PYTHON = "<absoluter Pfad zur Worker-python.exe>"
$env:SIRENS_RT_SAM_AUDIO_RECEIPT = "<absoluter Receipt-Pfad>"
& $env:SIRENS_RT_SAM_AUDIO_PYTHON -m benchmarks.semantic.messen --receipt $env:SIRENS_RT_SAM_AUDIO_RECEIPT --tracks <fuenf lokale WAVs> --out <neuer externer Ordner>
```

Benchmark nur explizit und nach Audit/Netzisolation starten. Der Worker bleibt unabhängig davon
in der Registry gesperrt. Die Datei manifest.json ist standardmäßig gesperrt; erst der Koordinator darf sie nach G1 und Installationsprüfung freigeben. Manifest und Freigabehaken siehe WP13. Rollback: Capability deaktivieren,
Worker beenden, Cache extern entfernen, bei Bedarf install.ps1 -Entfernen. Originale nicht ändern.

Technische Grenze: 15-Sekunden-Abschnitte ohne Overlap, mono Zielschätzung auf beide Kanäle,
PCM16-Residual als exakte Differenz unter gemeinsamer Begrenzung (0 LSB Rekonstruktionsfehler).
Keine Behauptung echter zeitlicher Isolation, Segmentübergänge und Qualität müssen gehört werden.
