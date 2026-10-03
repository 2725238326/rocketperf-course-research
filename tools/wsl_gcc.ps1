# Install GCC in an existing Ubuntu WSL distribution without changing its network.
[CmdletBinding()]
param(
    [string]$Distribution = 'Ubuntu',
    [string]$Snapshot = '20260201T000000Z',
    [switch]$Install
)
$ErrorActionPreference = 'Stop'
if ($Snapshot -notmatch '^\d{8}T\d{6}Z$') { throw 'Invalid Ubuntu snapshot timestamp.' }
$projectRoot = Split-Path $PSScriptRoot -Parent
$downloadRoot = Join-Path $projectRoot 'build/tooling/wsl-gcc-packages'
New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null
function Invoke-Ubuntu([string[]]$Arguments) {
    $lines = & wsl -d $Distribution -u root --exec @Arguments
    if ($LASTEXITCODE -ne 0) { throw "WSL command failed: $($Arguments[0])" }
    return $lines
}
$plan = Invoke-Ubuntu @('apt-get', '--print-uris', '--yes', 'install', 'gcc')
$packages = @()
foreach ($line in $plan) {
    if ($line -notmatch "^'(?<url>http://archive\.ubuntu\.com/ubuntu/[^']+)' (?<file>\S+) (?<size>\d+) MD5Sum:[a-f0-9]+$") { continue }
    $uri = $Matches.url
    $file = $Matches.file
    $size = [long]$Matches.size
    # The apt plan and cached metadata must identify exactly the same archive.
    $name = $file.Split('_')[0]
    $metadata = (Invoke-Ubuntu @('apt-cache', 'show', $name)) -join "`n"
    $archive = [Uri]::UnescapeDataString(([Uri]$uri).AbsolutePath.Substring('/ubuntu/'.Length))
    $matching = @($metadata -split "`n\s*`n" | Where-Object { $_ -match "(?m)^Filename: $([regex]::Escape($archive))$" })
    if ($matching.Count -ne 1 -or $matching[0] -notmatch '(?m)^SHA256: ([a-f0-9]{64})$') { throw "Missing unique SHA256 metadata: $file" }
    $sha256 = $Matches[1]
    $destination = Join-Path $downloadRoot $file
    if (-not (Test-Path -LiteralPath $destination) -or (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha256) {
        $url = "https://snapshot.ubuntu.com/ubuntu/$Snapshot/$archive"
        Write-Output "Download $file"
        Invoke-WebRequest -Uri $url -OutFile $destination -TimeoutSec 180
    }
    if ((Get-Item -LiteralPath $destination).Length -ne $size -or (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha256) { throw "Archive integrity failed: $file" }
    $packages += [ordered]@{file=$file; sha256=$sha256; bytes=$size; source="https://snapshot.ubuntu.com/ubuntu/$Snapshot/$archive"}
}
if ($packages.Count -eq 0) {
    Invoke-Ubuntu @('gcc', '--version')
    return
}
$packages | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $downloadRoot 'packages.json') -Encoding utf8
Write-Output "Verified $($packages.Count) archives against cached Ubuntu SHA256 metadata."
if (-not $Install) { Write-Output 'Download only. Use -Install to install GCC into the named WSL distribution.'; return }
foreach ($package in $packages) {
    $windowsPath = Join-Path $downloadRoot $package.file
    $linuxPath = (Invoke-Ubuntu @('wslpath', '-u', $windowsPath.Replace('\','/')) | Select-Object -Last 1).Trim()
    Invoke-Ubuntu @('cp', '--', $linuxPath, "/var/cache/apt/archives/$($package.file)") | Out-Null
}
# No upgrade, removal or distro networking change is requested.
Invoke-Ubuntu @('apt-get', '--yes', '--no-download', 'install', 'gcc')
Invoke-Ubuntu @('gcc', '--version')
