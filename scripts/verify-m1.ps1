$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv/Scripts/python.exe'
$priorAutoload = $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD
$priorPath = $env:PYTHONPATH
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
Start-Transcript -Path docs/implementation-evidence/M1/verification.txt -Force | Out-Null
try {
    & $python -m pytest -c pyproject.toml --confcutdir=tests/foundation tests/foundation --junitxml=docs/implementation-evidence/M1/foundation-regression.xml
    if ($LASTEXITCODE) { throw 'Foundation regression failed' }
    & $python -m pytest -c pyproject.toml --confcutdir=tests/trust tests/trust --junitxml=docs/implementation-evidence/M1/trust.xml
    if ($LASTEXITCODE) { throw 'M1 verification failed' }
    & npm.cmd run typecheck
    if ($LASTEXITCODE) { throw 'TypeScript validation failed' }
    & npm.cmd run build
    if ($LASTEXITCODE) { throw 'Web build failed' }
} finally {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = $priorAutoload
    $env:PYTHONPATH = $priorPath
    Stop-Transcript | Out-Null
}
