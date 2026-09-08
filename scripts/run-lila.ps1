param(
    [ValidateSet('setup','run','open','status','quit')][string]$Operation = 'run',
    [string]$DataDir = (Join-Path $env:LOCALAPPDATA 'LILAClaw')
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$priorPath = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $root 'src'
try {
    & (Join-Path $root '.venv/Scripts/python.exe') -m lila.runtime.launcher $Operation --data-dir $DataDir
    if ($LASTEXITCODE) { throw 'LILA launcher failed' }
} finally {
    $env:PYTHONPATH = $priorPath
}
