# Nur explizite Installation in der isolierten WSL2-Umgebung.
param([switch]$ModelleLaden, [switch]$Entfernen)
$ErrorActionPreference = 'Stop'
if ($ModelleLaden -and $Entfernen) { throw 'Schalter schließen sich aus' }
if (!$ModelleLaden -and !$Entfernen) {
    Write-Host 'Kein Netzbezug. Ubuntu 24.04/WSL2 mit Python 3.12 vorbereiten.'
    exit 0
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$flag = if ($ModelleLaden) { '--modelle-laden' } else { '--entfernen' }
& wsl.exe --cd $root --exec python3.12 -m workers.magenta.install $flag
if ($LASTEXITCODE -ne 0) { throw "WSL-Installation fehlgeschlagen: $LASTEXITCODE" }
