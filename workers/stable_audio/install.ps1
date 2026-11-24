# Nur explizite Installation, keine Gewichte oder Umgebungen im Repository.
param([Parameter(Mandatory=$true)][string]$InstallRoot, [switch]$ModelleLaden)
$ErrorActionPreference = 'Stop'
function Run($Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Installation fehlgeschlagen ($LASTEXITCODE)" }
}
$root = [IO.Path]::GetFullPath($InstallRoot)
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if ($root -eq $repo -or $root.StartsWith($repo + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'InstallRoot muss außerhalb des Repositorys liegen.'
}
New-Item -ItemType Directory -Force -Path $root | Out-Null
$venv = Join-Path $root 'venv'
$src = Join-Path $root 'sa3'
$cache = Join-Path $root 'hf-cache'
$pin = '790793b89ddceea612be9ce42ff6830d18f6fa57'
Run py @('-3.11','-m','venv',$venv)
$python = Join-Path $venv 'Scripts/python.exe'
if (!(Test-Path $src)) {
    Run git @('init',$src)
    Run git @('-C',$src,'remote','add','origin','https://github.com/Stability-AI/stable-audio-3.git')
}
Run git @('-C',$src,'fetch','--depth=1','https://github.com/Stability-AI/stable-audio-3.git',$pin)
Run git @('-C',$src,'checkout','--detach',$pin)
Run $python @('-m','pip','install','--only-binary=:all:','--index-url','https://download.pytorch.org/whl/cu128','torch==2.7.1+cu128','torchaudio==2.7.1+cu128')
Run $python @('-m','pip','install','--only-binary=:all:','-r',(Join-Path $PSScriptRoot 'requirements.lock'),'hatchling')
Run $python @('-m','pip','install','--no-deps','--no-build-isolation',$src)
$env:SIRENS_RT_STABLE_AUDIO_CACHE = $cache
if ($ModelleLaden) {
    if ((Read-Host 'HF-Lizenz bestätigt, lokaler Login erfolgt, Gewichte jetzt laden? (ja/nein)') -ne 'ja') { throw 'Abgebrochen' }
    $env:HF_HUB_CACHE = $cache
    Run $python @('-c', "from huggingface_hub import snapshot_download; snapshot_download('stabilityai/stable-audio-3-small-music', revision='8bdfb53c6b0fbc62113cd571fd37373efe15fa14', allow_patterns=['model.safetensors','model_config.json','t5gemma-b-b-ul2/model.safetensors','t5gemma-b-b-ul2/tokenizer.json','t5gemma-b-b-ul2/tokenizer.model'])")
    $refs = Join-Path $cache 'models--stabilityai--stable-audio-3-small-music/refs'
    New-Item -ItemType Directory -Force -Path $refs | Out-Null
    [IO.File]::WriteAllText((Join-Path $refs 'main'),'8bdfb53c6b0fbc62113cd571fd37373efe15fa14')
    Push-Location $PSScriptRoot
    try { Run $python @('-c','import os; from adapter import verify_cache; verify_cache(os.environ["SIRENS_RT_STABLE_AUDIO_CACHE"])') }
    finally { Pop-Location }
}
Write-Host "SIRENS_RT_STABLE_AUDIO_PYTHON=$python"
Write-Host "SIRENS_RT_STABLE_AUDIO_CACHE=$cache"
