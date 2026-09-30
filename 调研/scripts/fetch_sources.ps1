param([string]$Manifest = (Join-Path (Split-Path -Parent $PSScriptRoot) 'sources_to_fetch.json'))
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root '原始来源'
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
$sources = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
$sources | ForEach-Object -Parallel {
    $source = $_
    $outDir = $using:outDir
    $path = Join-Path $outDir ($source.id + '.txt')
    if (Test-Path -LiteralPath $path) { [pscustomobject]@{Id=$source.id; Status='exists'}; return }
    try {
        $res = Invoke-WebRequest -Uri $source.url -TimeoutSec 45 -Headers @{'User-Agent'='CourseResearch/1.0'}
        $text = [string]$res.Content
        [System.IO.File]::WriteAllText($path, $text, [System.Text.UTF8Encoding]::new($false))
        [pscustomobject]@{Id=$source.id; Url=$source.url; Status=[int]$res.StatusCode; Characters=$text.Length; File=$path; RetrievedAt=[DateTimeOffset]::Now.ToString('o')}
    } catch {
        [pscustomobject]@{Id=$source.id; Url=$source.url; Status='error'; Error=$_.Exception.Message}
    }
} -ThrottleLimit 6 | ForEach-Object {
    $_ | ConvertTo-Json -Compress
}
