param(
    [string]$Case = 'cases/benchmarks/air_mach2_vacuum.ini',
    [ValidateSet('Debug','Release')][string]$Configuration = 'Release',
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]{0,100}$')][string]$RunId = ('run_' + (Get-Date -Format 'yyyyMMdd_HHmmssfff') + '_' + [guid]::NewGuid().ToString('N').Substring(0,8))
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$casePath = if ([System.IO.Path]::IsPathRooted($Case)) { $Case } else { Join-Path $projectRoot $Case }
$casePath = (Resolve-Path -LiteralPath $casePath -ErrorAction Stop).Path
$runDir = Join-Path $projectRoot ('results/local/' + $RunId)
if (Test-Path -LiteralPath $runDir) { throw 'RunId already exists; old results will not be overwritten.' }
& (Join-Path $PSScriptRoot 'build.ps1') -Configuration $Configuration
$buildDir = Join-Path $projectRoot ('build/' + $Configuration.ToLowerInvariant())
$suffix = if ($IsWindows) { '.exe' } else { '' }
$exeName = 'rocketperf' + $suffix
[System.IO.Directory]::CreateDirectory($runDir) | Out-Null
$inputPath = Join-Path $runDir 'input.ini'
$binaryPath = Join-Path $runDir $exeName
Copy-Item -LiteralPath $casePath -Destination $inputPath
Copy-Item -LiteralPath (Join-Path $buildDir $exeName) -Destination $binaryPath
Copy-Item -LiteralPath (Join-Path $buildDir 'build-manifest.json') -Destination (Join-Path $runDir 'build-manifest.json')
$start = [System.Diagnostics.ProcessStartInfo]::new()
$start.FileName = $binaryPath
$start.WorkingDirectory = $projectRoot
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$start.RedirectStandardOutput = $true
$start.RedirectStandardError = $true
$start.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
$start.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)
$start.ArgumentList.Add('run')
$start.ArgumentList.Add($inputPath)
$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $start
try {
    if (-not $process.Start()) { throw 'Unable to start case process.' }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $timedOut = -not $process.WaitForExit(15000)
    if ($timedOut) { $process.Kill($true); $process.WaitForExit() }
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    $exitCode = $process.ExitCode
} finally { $process.Dispose() }
$validJson = $false
if ($exitCode -eq 0 -and -not $timedOut) {
    try { $null = $stdout | ConvertFrom-Json -ErrorAction Stop; $validJson = $true } catch { $stderr += "`nInvalid JSON result." }
}
$outputName = if ($validJson) { 'result.json' } else { 'stdout.txt' }
[System.IO.File]::WriteAllText((Join-Path $runDir $outputName), $stdout, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText((Join-Path $runDir 'stderr.txt'), $stderr, [System.Text.UTF8Encoding]::new($false))
$manifest = [ordered]@{
    schema_version=1; run_id=$RunId; finished_at=[DateTimeOffset]::Now.ToString('o')
    status=$(if ($validJson) {'SUCCESS'} else {'FAILED'}); exit_code=$exitCode; timed_out=$timedOut
    original_case_path=$casePath; command=@($exeName,'run','input.ini')
    input_sha256=(Get-FileHash -LiteralPath $inputPath).Hash
    executable_sha256=(Get-FileHash -LiteralPath $binaryPath).Hash
    build_manifest_sha256=(Get-FileHash -LiteralPath (Join-Path $runDir 'build-manifest.json')).Hash
    output_file=$outputName; output_sha256=(Get-FileHash -LiteralPath (Join-Path $runDir $outputName)).Hash
    validation_claim='Execution and provenance record only; consult separate test reports for validation.'
}
[System.IO.File]::WriteAllText((Join-Path $runDir 'run-manifest.json'), ($manifest | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))
if (-not $validJson) { throw "Case failed; diagnostics retained in $runDir" }
[pscustomobject]@{Status='SUCCESS'; RunDirectory=$runDir; Result=(Join-Path $runDir 'result.json')} | ConvertTo-Json
