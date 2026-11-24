# Explizite Installation in der isolierten DEMON-Umgebung des Messpfads.
param([switch]$ModelleLaden, [switch]$Entfernen)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$spike = Join-Path $root 'benchmarks/spikes/demon/install.ps1'
& $spike -ModelleLaden:$ModelleLaden -Entfernen:$Entfernen
if ($LASTEXITCODE -ne 0) { throw 'DEMON-Installation fehlgeschlagen' }
if (!$Entfernen) {
    $python = Join-Path $root '.venv-spike-demon/Scripts/python.exe'
    Write-Host "SIRENS_RT_DEMON_PYTHON=$python"
    Write-Host 'Keine Freigabe vor Gate G1; kein automatischer Download.'
}
