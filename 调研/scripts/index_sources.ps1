$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$records = @()
foreach ($file in (Get-ChildItem -LiteralPath $root -Filter '*sources*.json')) {
    foreach ($source in (Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json)) {
        $path = Join-Path $root ('原始来源/' + $source.id + '.txt')
        $exists = Test-Path -LiteralPath $path
        $record = [ordered]@{id=$source.id; url=$source.url; available=$exists}
        if ($exists) {
            $item = Get-Item -LiteralPath $path
            $record.file = $item.Name
            $record.bytes = $item.Length
            $record.saved_at = $item.LastWriteTimeUtc.ToString('o')
            $record.sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        }
        $records += [pscustomobject]$record
    }
}
$records = @($records | Sort-Object id -Unique)
$out = Join-Path $root '原始来源/来源文件索引.json'
[System.IO.File]::WriteAllText($out, ($records | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))
[pscustomobject]@{Sources=$records.Count; Available=@($records | Where-Object available).Count; Missing=@($records | Where-Object {-not $_.available} | ForEach-Object id)} | ConvertTo-Json -Depth 3
