$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv/Scripts/python.exe'
$priorAutoload = $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
Start-Transcript -Path docs/implementation-evidence/M0/verification.txt -Force | Out-Null
try {
    & $python -m pytest -c pyproject.toml --confcutdir=tests/foundation tests/foundation --junitxml=docs/implementation-evidence/M0/pytest.xml
    if ($LASTEXITCODE) { throw 'Foundation tests failed' }
    & npm.cmd run typecheck
    if ($LASTEXITCODE) { throw 'TypeScript validation failed' }
    & npm.cmd run build
    if ($LASTEXITCODE) { throw 'Web build failed' }
} finally {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = $priorAutoload
    Stop-Transcript | Out-Null
}
