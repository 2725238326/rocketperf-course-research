param(
    [ValidateSet('Debug','Release')][string]$Configuration = 'Debug',
    [string]$Python = 'python',
    [switch]$Sanitize
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'build.ps1') -Configuration $Configuration -Sanitize:$Sanitize
$folder = $Configuration.ToLowerInvariant()
if ($Sanitize) { $folder += '-sanitized' }
$buildDir = Join-Path $projectRoot ('build/' + $folder)
$suffix = if ($IsWindows) { '.exe' } else { '' }
Push-Location -LiteralPath $projectRoot
try {
    & (Join-Path $buildDir ('test_core' + $suffix))
    if ($LASTEXITCODE -ne 0) { throw 'Core validation failed.' }
    & $Python 'tests/test_cli.py' '--binary' (Join-Path $buildDir ('rocketperf' + $suffix))
    if ($LASTEXITCODE -ne 0) { throw 'CLI contract validation failed.' }
    $report = [ordered]@{
        schema_version=1; checked_at=[DateTimeOffset]::Now.ToString('o'); status='PASS'
        configuration=$Configuration; sanitizer_enabled=[bool]$Sanitize
        checks=@('C core analytic references and balance/scaling/domain checks','Python black-box CLI contract suite')
        binary_sha256=(Get-FileHash -LiteralPath (Join-Path $buildDir ('rocketperf' + $suffix))).Hash
        build_manifest_sha256=(Get-FileHash -LiteralPath (Join-Path $buildDir 'build-manifest.json')).Hash
        validation_inputs=@(Get-ChildItem -LiteralPath './tests','./cases/benchmarks' -Recurse -File | Where-Object {
            $_.Extension -in '.c','.py','.json','.ini'
        } | Sort-Object FullName | ForEach-Object {
            [ordered]@{path=[System.IO.Path]::GetRelativePath($projectRoot,$_.FullName);sha256=(Get-FileHash -LiteralPath $_.FullName).Hash}
        })
        scope='Ideal-gas synthetic benchmark and software contracts, not real engine validation.'
    }
    [System.IO.File]::WriteAllText((Join-Path $buildDir 'test-report.json'), ($report | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))
    Write-Host "PASS: $Configuration core and CLI checks."
} finally { Pop-Location }
