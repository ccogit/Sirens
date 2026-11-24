# Isolierte lokale Umgebung; absichtlich kein Netzbezug ohne geprüfte Pins.
param([switch]$ModelleLaden, [switch]$Entfernen)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$venv = Join-Path $root '.venv-spike-after'
if ($Entfernen) {
    if (Test-Path -LiteralPath $venv) { Remove-Item -LiteralPath $venv -Recurse -Force }
    exit 0
}
if ($ModelleLaden) {
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'BERICHT.md')
    $answer = Read-Host 'Quellen, Größen und Lizenzen geprüft? (ja/nein)'
    if ($answer -ne 'ja') { throw 'Abgebrochen' }
    throw 'Automatischer Bezug noch nicht freigegeben: unveränderliche Pins und Hashes fehlen. Siehe Bericht.'
}
if (!(Test-Path -LiteralPath $venv)) {
    & py -3.12 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Erstellen der eigenen Umgebung fehlgeschlagen' }
}
Write-Host "Isolierte Umgebung: $venv. Abhängigkeiten/Gewichte noch nicht installiert."
