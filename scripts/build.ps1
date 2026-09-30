param(
    [ValidateSet('Debug','Release')][string]$Configuration = 'Debug',
    [string]$Compiler = 'gcc',
    [switch]$Sanitize
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$tool = (Get-Command $Compiler -ErrorAction Stop).Source
$buildDir = Join-Path $projectRoot ('build/' + $Configuration.ToLowerInvariant())
if ($Sanitize) {
    if ($IsWindows) { throw 'Sanitizers are configured only for the Linux GCC validation path.' }
    $buildDir += '-sanitized'
}
[System.IO.Directory]::CreateDirectory($buildDir) | Out-Null
$flags = @('-std=c17','-Wall','-Wextra','-Wpedantic','-Werror','-Wconversion','-Wshadow','-Wstrict-prototypes','-Wmissing-prototypes','-fno-common','-Iinclude','-Isrc/adapters')
if ($Configuration -eq 'Debug') { $flags += @('-O0','-g3') } else { $flags += @('-O2','-DNDEBUG') }
if ($Sanitize) { $flags += @('-fsanitize=address,undefined','-fno-omit-frame-pointer') }
$core = @('src/core/status.c','src/core/root.c','src/nozzle/ideal.c')
$adapters = @('src/adapters/case_file.c','src/adapters/json_report.c','src/adapters/platform.c')
$suffix = if ($IsWindows) { '.exe' } else { '' }
$app = Join-Path $buildDir ('rocketperf' + $suffix)
$test = Join-Path $buildDir ('test_core' + $suffix)
$appFlags = @($flags)
if ($IsWindows) { $appFlags += '-municode' }
Push-Location -LiteralPath $projectRoot
try {
    $versionLines = @(& $tool --version)
    if ($LASTEXITCODE -ne 0) { throw 'Compiler version check failed.' }
    $compilerVersion = $versionLines[0]
    & $tool @appFlags @core @adapters 'src/cli/main.c' '-lm' '-o' $app
    if ($LASTEXITCODE -ne 0) { throw 'Application build failed; do not use stale artifacts.' }
    & $tool @flags @core 'tests/test_core.c' '-lm' '-o' $test
    if ($LASTEXITCODE -ne 0) { throw 'Core test build failed.' }
    $sourceFiles = @($core + $adapters + @('src/cli/main.c','tests/test_core.c'))
    $sourceFiles += @(Get-ChildItem -LiteralPath './include','./src/adapters' -Recurse -File -Filter '*.h' | ForEach-Object { [System.IO.Path]::GetRelativePath($projectRoot, $_.FullName).Replace('\','/') })
    $sourceFiles += @('scripts/build.ps1')
    $inputs = @($sourceFiles | Sort-Object -Unique | ForEach-Object {
        [ordered]@{path=$_; sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}
    })
    $manifest = [ordered]@{
        schema_version=1; built_at=[DateTimeOffset]::Now.ToString('o')
        configuration=$Configuration; compiler=$tool; compiler_version=$compilerVersion
        flags=$flags; app_flags=$appFlags; sanitizer_enabled=[bool]$Sanitize
        inputs=$inputs
        application=[ordered]@{path=$app;sha256=(Get-FileHash -LiteralPath $app).Hash}
        core_test=[ordered]@{path=$test;sha256=(Get-FileHash -LiteralPath $test).Hash}
    }
    [System.IO.File]::WriteAllText((Join-Path $buildDir 'build-manifest.json'), ($manifest | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
    Write-Host "Built $Configuration with strict C17 warnings: $app"
} finally { Pop-Location }
