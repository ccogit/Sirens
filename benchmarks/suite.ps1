[CmdletBinding()]
param(
    [switch]$DryRun,
    [string]$OutputDir = (Join-Path ([IO.Path]::GetTempPath()) ("sirens-g4-" + [guid]::NewGuid())),
    [string]$MusicRoot,
    [string]$Plan,
    [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $arguments = @("-m", "benchmarks.system_suite", "--out", $OutputDir)
    if ($DryRun) { $arguments += "--dry-run" }
    if ($MusicRoot) { $arguments += @("--music-root", $MusicRoot) }
    if ($Plan) { $arguments += @("--plan", $Plan) }
    & $Python @arguments
    if ($LASTEXITCODE -ne 0) { throw "Systemabnahme fehlgeschlagen (Exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}
