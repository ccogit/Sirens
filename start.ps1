# Startet den Sirens-Dienst im Hintergrund ohne Fenster und meldet die Adresse.
#   .\start.ps1          starten (oder melden, dass er schon läuft)
#   .\start.ps1 -Stop    beenden
#   .\start.ps1 -Open    starten und die Seite im Standardbrowser öffnen
param([switch]$Stop, [switch]$Open)

$ErrorActionPreference = 'Stop'
$port = if ($env:SIRENS_PORT) { [int]$env:SIRENS_PORT } elseif ($env:SONG_AUFTRAG_PORT) { [int]$env:SONG_AUFTRAG_PORT } else { 8093 }
$adresse = "http://127.0.0.1:$port/"

function Get-Dienst {
    try { Invoke-RestMethod -Uri "${adresse}api/health" -TimeoutSec 2 } catch { $null }
}

$dienst = Get-Dienst
if ($Stop) {
    if (-not $dienst) { Write-Output "Sirens läuft nicht."; exit 0 }
    Stop-Process -Id $dienst.pid -Force
    Write-Output "Sirens beendet (Prozess $($dienst.pid))."
    exit 0
}

if (-not $dienst) {
    $protokoll = Join-Path $env:TEMP 'sirens'
    New-Item -ItemType Directory -Force $protokoll | Out-Null
    Start-Process -FilePath 'py' -ArgumentList '-3.11', '-m', 'sirens', 'serve' `
        -WorkingDirectory $PSScriptRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $protokoll 'dienst.out.log') `
        -RedirectStandardError (Join-Path $protokoll 'dienst.err.log') | Out-Null
    foreach ($i in 1..40) {
        Start-Sleep -Milliseconds 250
        $dienst = Get-Dienst
        if ($dienst) { break }
    }
    if (-not $dienst) {
        Write-Output "Sirens ist nicht gestartet. Protokoll: $protokoll\dienst.err.log"
        exit 1
    }
}

Write-Output "Sirens läuft: $adresse"
Write-Output "Musikordner: $($dienst.music_root) (vorhanden: $($dienst.music_root_vorhanden)) · Aufträge: $($dienst.data_dir)"
if ($Open) { Start-Process $adresse }
