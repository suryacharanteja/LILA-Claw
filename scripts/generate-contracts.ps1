$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& .venv/Scripts/datamodel-codegen.exe --input docs/lld/contracts/protocol-v1.schema.json --input-file-type jsonschema --output src/lila/contracts/generated_models.py --output-model-type pydantic_v2.BaseModel --target-python-version 3.12 --disable-timestamp --use-annotated --field-constraints
if ($LASTEXITCODE) { throw 'Python generation failed' }
& npm.cmd run generate:contracts
if ($LASTEXITCODE) { throw 'TypeScript generation failed' }
