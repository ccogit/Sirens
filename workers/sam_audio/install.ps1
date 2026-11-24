# Explizite Installation aus lokalem, vollständig gehashtem Wheelhouse.
param([switch]$Installieren, [switch]$Entfernen,
      [string]$Wheelhouse, [string]$GepruefterLock, [string]$Receipt)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$venv = Join-Path $root '.venv-sam-audio'
if ($Entfernen) {
    if (Test-Path -LiteralPath $venv) { Remove-Item -LiteralPath $venv -Recurse -Force }
    exit 0
}
if (!$Installieren) {
    Write-Host 'Nicht installiert / nicht gemessen. Kein Download. Siehe WP13.'
    exit 0
}
if (!$Wheelhouse -or !$GepruefterLock -or !$Receipt) {
    throw 'Geprüftes lokales Wheelhouse, vollständiger Hash-Lock und Snapshot-Receipt erforderlich.'
}
$wheelPath = (Resolve-Path -LiteralPath $Wheelhouse).Path
$lockPath = (Resolve-Path -LiteralPath $GepruefterLock).Path
$receiptPath = (Resolve-Path -LiteralPath $Receipt).Path
# Keine URLs, direkten Referenzen oder pip-Optionen im externen Lock.
foreach ($line in Get-Content -LiteralPath $lockPath) {
    if ($line -notmatch '^\s*(#.*)?        throw 'Nur lokale, gepinnte Wheels mit SHA-256 erlaubt.'
    }
}
& py -3.11 -m venv $venv
if ($LASTEXITCODE -ne 0) { throw 'venv konnte nicht erstellt werden' }
$python = Join-Path $venv 'Scripts/python.exe'
& $python -m pip --isolated install --no-index --no-deps --only-binary=:all: --require-hashes --find-links $wheelPath -r $lockPath
if ($LASTEXITCODE -ne 0) { throw 'Wheel-Installation fehlgeschlagen' }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Abhängigkeiten unvollständig' }
& $python -c "import importlib.metadata as m; assert m.version('torch') == '2.7.1+cu128'; assert m.version('torchaudio') == '2.7.1+cu128'; assert m.version('torchvision') == '0.22.1+cu128'; assert m.version('sam_audio') == '0.1.0'"
if ($LASTEXITCODE -ne 0) { throw 'Versionsprüfung fehlgeschlagen' }
Push-Location $PSScriptRoot
try {
    & $python -c "from backend import verify_snapshot; import sys; verify_snapshot(sys.argv[1])" $receiptPath
    if ($LASTEXITCODE -ne 0) { throw 'Snapshot-Prüfung fehlgeschlagen' }
} finally { Pop-Location }
Write-Host 'Lokale Installation geprüft; Capability bleibt bis G1 gesperrt.'
Write-Host "SIRENS_RT_SAM_AUDIO_PYTHON=$python"
Write-Host "SIRENS_RT_SAM_AUDIO_RECEIPT=$receiptPath"
 -and $line -notmatch '^\s*[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+(\s+--hash=sha256:[a-fA-F0-9]{64})+\s*        throw 'Nur lokale, gepinnte Wheels mit SHA-256 erlaubt.'
    }
}
& py -3.11 -m venv $venv
if ($LASTEXITCODE -ne 0) { throw 'venv konnte nicht erstellt werden' }
$python = Join-Path $venv 'Scripts/python.exe'
& $python -m pip --isolated install --no-index --only-binary=:all: --require-hashes --find-links $wheelPath -r $lockPath
if ($LASTEXITCODE -ne 0) { throw 'Wheel-Installation fehlgeschlagen' }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Abhängigkeiten unvollständig' }
& $python -c "import importlib.metadata as m; assert m.version('torch') == '2.7.1+cu128'; assert m.version('torchaudio') == '2.7.1+cu128'; assert m.version('torchvision') == '0.22.1+cu128'; assert m.version('sam_audio') == '0.1.0'"
if ($LASTEXITCODE -ne 0) { throw 'Versionsprüfung fehlgeschlagen' }
Push-Location $PSScriptRoot
try {
    & $python -c "from backend import verify_snapshot; import sys; verify_snapshot(sys.argv[1])" $receiptPath
    if ($LASTEXITCODE -ne 0) { throw 'Snapshot-Prüfung fehlgeschlagen' }
} finally { Pop-Location }
Write-Host 'Lokale Installation geprüft; Capability bleibt bis G1 gesperrt.'
Write-Host "SIRENS_RT_SAM_AUDIO_PYTHON=$python"
Write-Host "SIRENS_RT_SAM_AUDIO_RECEIPT=$receiptPath"
) {
        throw 'Nur lokale, gepinnte Wheels mit SHA-256 erlaubt.'
    }
}
& py -3.11 -m venv $venv
if ($LASTEXITCODE -ne 0) { throw 'venv konnte nicht erstellt werden' }
$python = Join-Path $venv 'Scripts/python.exe'
& $python -m pip --isolated install --no-index --only-binary=:all: --require-hashes --find-links $wheelPath -r $lockPath
if ($LASTEXITCODE -ne 0) { throw 'Wheel-Installation fehlgeschlagen' }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Abhängigkeiten unvollständig' }
& $python -c "import importlib.metadata as m; assert m.version('torch') == '2.7.1+cu128'; assert m.version('torchaudio') == '2.7.1+cu128'; assert m.version('torchvision') == '0.22.1+cu128'; assert m.version('sam_audio') == '0.1.0'"
if ($LASTEXITCODE -ne 0) { throw 'Versionsprüfung fehlgeschlagen' }
Push-Location $PSScriptRoot
try {
    & $python -c "from backend import verify_snapshot; import sys; verify_snapshot(sys.argv[1])" $receiptPath
    if ($LASTEXITCODE -ne 0) { throw 'Snapshot-Prüfung fehlgeschlagen' }
} finally { Pop-Location }
Write-Host 'Lokale Installation geprüft; Capability bleibt bis G1 gesperrt.'
Write-Host "SIRENS_RT_SAM_AUDIO_PYTHON=$python"
Write-Host "SIRENS_RT_SAM_AUDIO_RECEIPT=$receiptPath"
