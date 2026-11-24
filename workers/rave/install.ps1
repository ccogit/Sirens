# Bewusst dieselbe isolierte Umgebung wie der gepinnte G1-Messpfad.
param([switch]$ModelleLaden, [switch]$Entfernen)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$spike = Join-Path $root 'benchmarks/spikes/rave/install.ps1'
$venv = Join-Path $root '.venv-spike-rave'
& $spike -ModelleLaden:$ModelleLaden -Entfernen:$Entfernen
if ($LASTEXITCODE -ne 0) { throw 'RAVE-Installation fehlgeschlagen' }
if ($ModelleLaden -and !$Entfernen) {
    Set-Content -LiteralPath (Join-Path $venv 'weights/rave-trusted.txt') -Encoding ascii -Value '02458214e23890d6818504319a5b9903eabfe87a524491f6524f453e7f3dbcf0'
}
if (!$Entfernen) { Write-Host "SIRENS_RT_RAVE_PYTHON=$(Join-Path $venv 'Scripts/python.exe')" }
