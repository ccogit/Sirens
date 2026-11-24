# Opt-in-Rollout; keine Änderung der .env oder globaler Python-Umgebungen.
[CmdletBinding()]
param(
    [ValidateSet('demon','rave','after','magenta','sam_audio','separation','stable_audio')]
    [string[]]$Worker = @('demon','rave','after','magenta','sam_audio','separation','stable_audio'),
    [switch]$DryRun, [switch]$ModelleLaden, [switch]$Entfernen,
    [string]$LokalerExport, [string]$Sha256, [string]$Gewichtslizenz,
    [string]$Wheelhouse, [string]$GepruefterLock, [string]$Receipt
)
$ErrorActionPreference = 'Stop'
if ($ModelleLaden -and $Entfernen) { throw 'Schalter schließen sich aus.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Worker = @($Worker | Select-Object -Unique)
$external = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'Sirens' } else { '<LOCALAPPDATA>/Sirens' }
$targets = @{
    demon = Join-Path $root '.venv-spike-demon'
    rave = Join-Path $root '.venv-spike-rave'
    after = Join-Path $root '.venv-spike-after'
    sam_audio = Join-Path $root '.venv-sam-audio'
    separation = Join-Path $external 'rt-rollout-separation'
    stable_audio = Join-Path $external 'rt-rollout-stable-audio'
    magenta = 'WSL: ~/.venv-worker-magenta'
}
Write-Output 'Rückfall: Dienst beenden, SIRENS_RT_ENABLED=0 in .env setzen, neu starten.'
Write-Output 'Diagnose: py -3.11, nvidia-smi (Treiber/CUDA/VRAM), freier Speicher auf Zielvolumes; Magenta: WSL2 separat.'
foreach ($w in $Worker) {
    $action = if ($Entfernen) { 'Entfernen (nur eigenes Ziel)' } elseif ($ModelleLaden) { 'Opt-in Installation nach Zustimmung' } else { 'Nur Diagnose, kein Bezug' }
    Write-Output "$w : $action -> $($targets[$w]); workers/$w/install.ps1"
}
if ($DryRun) { return }
if ($env:OS -ne 'Windows_NT' -or !$env:LOCALAPPDATA) { throw 'Windows mit LOCALAPPDATA erforderlich.' }
# Niemals durch Links/Junctions in fremde Daten löschen oder schreiben.
function Assert-Ordner([string]$path) {
    $p = [IO.Path]::GetFullPath($path)
    while ($p) {
        if (Test-Path -LiteralPath $p) {
            $item = Get-Item -LiteralPath $p -Force
            if (!$item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw "Kein sicherer Ordner: $p"
            }
        }
        $p = [IO.Path]::GetDirectoryName($p)
    }
}
function Assert-Baum([string]$path) {
    Assert-Ordner $path
    if (Test-Path -LiteralPath $path) {
        foreach ($item in Get-ChildItem -LiteralPath $path -Force) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Link im Ziel: $($item.FullName)" }
            if ($item.PSIsContainer) { Assert-Baum $item.FullName }
        }
    }
}
if ($Entfernen) {
    foreach ($w in $Worker) {
        if ($w -eq 'magenta') {
            Write-Warning 'Magenta separat in WSL prüfen und über workers/magenta/install.ps1 -Entfernen entfernen.'
            continue
        }
        $target = $targets[$w]
        Assert-Baum $target
        if (Test-Path -LiteralPath $target) {
            if (!(Test-Path -LiteralPath (Join-Path $target '.sirens-rt-rollout') -PathType Leaf)) {
                throw "Keine Rollout-Markierung; Bestandsumgebung bleibt erhalten: $target"
            }
            Remove-Item -LiteralPath $target -Recurse -Force
        }
    }
    return
}
& py -3.11 --version
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 fehlt.' }
& nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv
if ($LASTEXITCODE -ne 0) { throw 'NVIDIA-Treiberdiagnose fehlgeschlagen.' }
& nvidia-smi
if ($LASTEXITCODE -ne 0) { throw 'CUDA-Treiberdiagnose fehlgeschlagen.' }
foreach ($w in $Worker) {
    if ($w -eq 'magenta') { & wsl.exe --list --verbose; continue }
    $target = $targets[$w]
    Assert-Ordner $target
    $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($target))
    Write-Output "$w : freier Speicher $($drive.AvailableFreeSpace) Bytes"
    if ($drive.AvailableFreeSpace -le 0) { throw "Kein freier Speicher: $target" }
}
if (!$ModelleLaden) { return }
# Keine automatische Freigabe: Betreiber prüft die ausgegebenen Ressourcen,
# Modelllizenzen und die jeweiligen Locks/Hashes vor dem Bezug.
if ((Read-Host 'Treiber, CUDA, freier Speicher, VRAM, Quellen und Lizenzen geprüft; ausgewählte Worker installieren? (ja/nein)') -cne 'ja') {
    throw 'Installation abgebrochen.'
}
foreach ($w in $Worker) {
    $installer = Join-Path $root "workers/$w/install.ps1"
    if ($w -eq 'magenta') {
        & $installer -ModelleLaden
        if ($LASTEXITCODE -ne 0) { throw "$w fehlgeschlagen" }
        continue
    }
    $target = $targets[$w]
    Assert-Baum $target
    if (Test-Path -LiteralPath $target) {
        if (!(Test-Path -LiteralPath (Join-Path $target '.sirens-rt-rollout') -PathType Leaf)) {
            throw "Bestandsumgebung nicht übernehmen: $target"
        }
    } else {
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        # Spike-Installer erwarten einen noch nicht existierenden venv-Ordner.
        if ($w -in @('demon','rave','after')) {
            & py -3.11 -m venv $target
            if ($LASTEXITCODE -ne 0) { throw 'venv fehlgeschlagen' }
        }
        Set-Content -LiteralPath (Join-Path $target '.sirens-rt-rollout') -Value $w
    }
    switch ($w) {
        'separation' { & $installer -ModelleLaden -Umgebung $target }
        'stable_audio' { & $installer -ModelleLaden -InstallRoot $target }
        'sam_audio' { & $installer -Installieren -Wheelhouse $Wheelhouse -GepruefterLock $GepruefterLock -Receipt $Receipt }
        'after' { & $installer -ModelleLaden -LokalerExport $LokalerExport -Sha256 $Sha256 -Gewichtslizenz $Gewichtslizenz }
        default { & $installer -ModelleLaden }
    }
    if ($LASTEXITCODE -ne 0) { throw "$w fehlgeschlagen" }
}
Write-Output 'Installation ist keine Gate-Freigabe. Flag bleibt unverändert.'
