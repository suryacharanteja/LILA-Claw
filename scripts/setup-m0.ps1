param(
    [Parameter(Mandatory=$true)][string]$Python312
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& $Python312 -c "import sys,platform; assert sys.version_info[:3] == (3,12,14) and platform.machine() == 'AMD64'"
if ($LASTEXITCODE) { throw 'Use the qualified CPython 3.12.14 Windows x64 build' }
& uv --cache-dir .uv-cache venv --python $Python312 .venv
if ($LASTEXITCODE) { throw 'Environment creation failed' }
& uv --cache-dir .uv-cache pip sync requirements.lock --python .venv/Scripts/python.exe --require-hashes
if ($LASTEXITCODE) { throw 'Hash-locked Python install failed' }
& npm.cmd ci --ignore-scripts --cache .npm-cache
if ($LASTEXITCODE) { throw 'npm lock install failed' }
