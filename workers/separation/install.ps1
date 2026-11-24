param([switch]$ModelleLaden, [string]$Umgebung = "$env:LOCALAPPDATA\Sirens\separation")
$ErrorActionPreference = 'Stop'
if (-not $ModelleLaden) {
    Write-Output 'Kein Bezug ohne -ModelleLaden.'
    exit 0
}
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Umgebung = [IO.Path]::GetFullPath($Umgebung)
if ($Umgebung.StartsWith($Root + '\', [StringComparison]::OrdinalIgnoreCase) -or $Umgebung -eq $Root) {
    throw 'Umgebung muss außerhalb des Repositorys liegen.'
}
function Run([string]$Exe, [string[]]$Argumente) {
    & $Exe @Argumente
    if ($LASTEXITCODE -ne 0) { throw "Installation fehlgeschlagen ($LASTEXITCODE)." }
}
Run 'py' @('-3.11','-m','venv',$Umgebung)
$Python = Join-Path $Umgebung 'Scripts\python.exe'
$MSST = Join-Path $Umgebung 'msst'
$Pin = '1523206d12a521bdb20673726562524cf0f9635b'
if (-not (Test-Path $MSST)) {
    Run 'git' @('init',$MSST)
    Run 'git' @('-C',$MSST,'fetch','--depth=1','https://github.com/ZFTurbo/Music-Source-Separation-Training.git',$Pin)
    Run 'git' @('-C',$MSST,'checkout','--detach','FETCH_HEAD')
}
if ((& git -C $MSST rev-parse HEAD) -ne $Pin -or (& git -C $MSST status --porcelain)) {
    throw 'Ungeprüfter MSST-Arbeitsbaum.'
}
$Pins = @(Get-Content (Join-Path $PSScriptRoot 'requirements.lock') | Where-Object { $_ -and -not $_.StartsWith('#') })
Run $Python (@('-m','pip','install','--index-url','https://download.pytorch.org/whl/cu128') + $Pins[0..1])
Run $Python (@('-m','pip','install','--index-url','https://pypi.org/simple') + $Pins[2..($Pins.Length-1)])
Run $Python @('-m','pip','check')
Run $Python @('-c','import torch; assert torch.__version__ == "2.7.1+cu128" and torch.cuda.is_available()')
$Spike = Join-Path $Root 'benchmarks\spikes\roformer-drumsep\install.py'
Run $Python @('-c','import json, pathlib, runpy, sys; p = pathlib.Path(sys.argv[1]); m = runpy.run_path(str(p)); m["obtain_weight"](json.loads((p.parent / "weights.json").read_text(encoding="utf-8"))["models"][0], pathlib.Path(sys.prefix) / "weights")',$Spike)
Copy-Item (Join-Path $PSScriptRoot 'manifest.template.json') (Join-Path $PSScriptRoot 'manifest.json') -Force
Write-Output "Lokal in .env setzen: SIRENS_RT_SEPARATION_PYTHON=$Python"
Write-Output 'manifest.json ist ein lokales Installationsartefakt; nicht committen.'
