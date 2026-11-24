# Bewusst dieselbe isolierte Umgebung wie der gepinnte G1-Messpfad.
param([switch]$ModelleLaden, [switch]$Entfernen, [string]$LokalerExport, [string]$Sha256, [string]$Gewichtslizenz)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
& (Join-Path $root 'benchmarks/spikes/after/install.ps1') -ModelleLaden:$ModelleLaden -Entfernen:$Entfernen -LokalerExport $LokalerExport -Sha256 $Sha256 -Gewichtslizenz $Gewichtslizenz
if ($LASTEXITCODE -ne 0) { throw 'AFTER-Installation fehlgeschlagen' }
if (!$Entfernen) { Write-Host "SIRENS_RT_AFTER_PYTHON=$(Join-Path $root '.venv-spike-after/Scripts/python.exe')" }
