$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv/Scripts/python.exe'
$evidence = 'docs/implementation-evidence/M2'
New-Item -ItemType Directory -Force -Path $evidence | Out-Null
$priorAutoload = $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD
$priorPath = $env:PYTHONPATH
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
Start-Transcript -Path "$evidence/verification.txt" -Force | Out-Null
try {
    foreach ($suite in @('foundation','trust','domain')) {
        & $python -m pytest -c pyproject.toml "--confcutdir=tests/$suite" "tests/$suite" "--junitxml=$evidence/$suite.xml"
        if ($LASTEXITCODE) { throw "$suite verification failed" }
    }
    & npm.cmd run typecheck
    if ($LASTEXITCODE) { throw 'TypeScript validation failed' }
    & npm.cmd run build
    if ($LASTEXITCODE) { throw 'Web build failed' }
} finally {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = $priorAutoload
    $env:PYTHONPATH = $priorPath
    Stop-Transcript | Out-Null
}
