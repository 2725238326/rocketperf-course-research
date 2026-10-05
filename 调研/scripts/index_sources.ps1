param([string]$Manifest = '调研/sources_to_fetch.json')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location -LiteralPath $projectRoot
try {
    # Append one explicit manifest. Top-level glob regeneration would drop nested archives.
    python tools/feed_candidates.py register-sources --source-manifest $Manifest
    if ($LASTEXITCODE -ne 0) { throw 'Source registration failed; index was not replaced.' }
} finally {
    Pop-Location
}
