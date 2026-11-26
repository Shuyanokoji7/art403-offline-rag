$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:PYTHONUTF8 = '1'
python -m local_rag.bootstrap
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m local_rag index
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m local_rag doctor --verify
exit $LASTEXITCODE
