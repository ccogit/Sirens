# Isolierte lokale Umgebung, Bezug ausschließlich nach ausdrücklicher Bestätigung.
param([switch]$ModelleLaden, [switch]$Entfernen)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$venv = Join-Path $root '.venv-spike-roformer-drumsep'
if ($Entfernen) {
    if (Test-Path -LiteralPath $venv) { Remove-Item -LiteralPath $venv -Recurse -Force }
    exit 0
}
if (!(Test-Path -LiteralPath $venv)) {
    & py -3.11 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Erstellen der eigenen Umgebung fehlgeschlagen' }
}
if ($ModelleLaden) {
    & (Join-Path $venv 'Scripts/python.exe') (Join-Path $PSScriptRoot 'install.py') --modelle-laden
    if ($LASTEXITCODE -ne 0) { throw 'Bezug abgebrochen oder fehlgeschlagen' }
}
Write-Host "Isolierte Umgebung: $venv. DrumSep noch nicht freigegeben."
