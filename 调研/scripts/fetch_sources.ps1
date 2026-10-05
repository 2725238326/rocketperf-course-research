param([string]$Manifest = (Join-Path (Split-Path -Parent $PSScriptRoot) 'sources_to_fetch.json'))
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root '原始来源'
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
$sources = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
$sources | ForEach-Object -Parallel {
    $source = $_
    $outDir = $using:outDir
    $relative = if ($source.file) { [string]$source.file } else { $source.id + '.txt' }
    $path = [System.IO.Path]::GetFullPath((Join-Path $outDir $relative))
    $prefix = [System.IO.Path]::GetFullPath($outDir) + [System.IO.Path]::DirectorySeparatorChar
    if ([System.IO.Path]::IsPathRooted($relative) -or -not $path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Source output path escapes the archive directory.'
    }
    if (Test-Path -LiteralPath $path) { [pscustomobject]@{Id=$source.id; Status='exists'}; return }
    try {
        [System.IO.Directory]::CreateDirectory((Split-Path -Parent $path)) | Out-Null
        if ([System.IO.Path]::GetExtension($path) -eq '.pdf') {
            Invoke-WebRequest -Uri $source.url -OutFile $path -TimeoutSec 45 -Headers @{'User-Agent'='CourseResearch/1.0'}
            [pscustomobject]@{Id=$source.id; Url=$source.url; Status='downloaded'; Bytes=(Get-Item -LiteralPath $path).Length; File=$path; RetrievedAt=[DateTimeOffset]::Now.ToString('o')}
            return
        }
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
