param([switch]$LexicalRetrieval)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:PYTHONUTF8 = '1'
if ($LexicalRetrieval) {
    python -m local_rag chat --lexical
} else {
    python -m local_rag chat
}
exit $LASTEXITCODE
