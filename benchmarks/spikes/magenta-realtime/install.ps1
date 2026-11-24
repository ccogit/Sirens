# WSL2 statt nativer Windows-JAX-CUDA-Installation.
param([switch]$ModelleLaden, [switch]$Entfernen)
$ErrorActionPreference = 'Stop'
if ($ModelleLaden -and $Entfernen) { throw 'Schalter schließen sich aus' }
if (!$ModelleLaden -and !$Entfernen) {
    Write-Host 'Kein Netzbezug. WSL2 mit Python 3.12 vorbereiten; siehe BERICHT.md.'
    exit 0
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$flag = if ($ModelleLaden) { '--modelle-laden' } else { '--entfernen' }
& wsl.exe --cd $root python3.12 -m benchmarks.spikes.magenta-realtime.install $flag
if ($LASTEXITCODE -ne 0) { throw "WSL-Installation fehlgeschlagen: $LASTEXITCODE" }
