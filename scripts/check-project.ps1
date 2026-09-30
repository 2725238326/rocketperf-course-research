param([switch]$SkipHashes)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$issues = [System.Collections.Generic.List[string]]::new()
$required = @(
    'AGENTS.md','README.md','worknow.md','rules.md','handoff.md',
    'docs/project-map.md','docs/requirements-map.md','docs/tasks.md',
    'docs/research-agenda.md','docs/decisions.md','docs/verification.md','docs/environment.md',
    'docs/templates/research-note.md','docs/templates/port-review.md',
    'taskshot/README.md','taskshot/_template.md',
    '作业要求/大作业1_要求存档.md','调研/README.md','调研/专题/README.md',
    '调研/原始来源/来源文件索引.json','调研/scripts/research.ps1',
    'docs/engineering.md','docs/benchmarks.md','docs/case-format.md',
    'include/rocketperf/nozzle.h','src/nozzle/ideal.c','src/cli/main.c',
    'cases/benchmarks/air_mach2_vacuum.ini','tests/reference/air_mach2.json',
    'tests/test_core.c','tests/test_cli.py','scripts/build.ps1','scripts/test.ps1','scripts/run-case.ps1'
)
foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $relative) -PathType Leaf)) {
        $issues.Add("Missing required file: $relative")
    }
}
$docs = @(Get-ChildItem -LiteralPath $projectRoot -Recurse -File -Filter '*.md' | Where-Object {
    $_.FullName -notmatch '[\\/](原始来源|文献|检索记录|\.git|build|third_party)[\\/]'
})
$linkCount = 0
foreach ($doc in $docs) {
    $content = Get-Content -LiteralPath $doc.FullName -Raw
    foreach ($match in [regex]::Matches($content, '\]\((?<target>[^)\r\n]+)\)')) {
        $target = $match.Groups['target'].Value.Trim().Trim('<','>')
        if ($target -match '^[a-zA-Z][a-zA-Z0-9+.-]*://' -or $target -match '^(mailto:|#)') { continue }
        $target = [uri]::UnescapeDataString(($target -split '#',2)[0])
        if (-not $target) { continue }
        $linkCount++
        $resolved = if ([System.IO.Path]::IsPathRooted($target)) { $target } else { Join-Path $doc.DirectoryName $target }
        if (-not (Test-Path -LiteralPath $resolved)) { $issues.Add("Broken local link in $($doc.Name): $target") }
    }
}
$scripts = @(Get-ChildItem -LiteralPath $projectRoot -Recurse -File -Filter '*.ps1')
foreach ($script in $scripts) {
    $tokens = $null
    $parseErrors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($script.FullName, [ref]$tokens, [ref]$parseErrors)
    foreach ($problem in $parseErrors) { $issues.Add("PowerShell syntax: $($script.Name): $($problem.Message)") }
}
$indexPath = Join-Path $projectRoot '调研/原始来源/来源文件索引.json'
$index = @(Get-Content -LiteralPath $indexPath -Raw | ConvertFrom-Json)
$verifiedHashes = 0
foreach ($record in $index) {
    if (-not $record.available) { continue }
    $path = Join-Path $projectRoot ('调研/原始来源/' + $record.file)
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $issues.Add("Indexed source missing: $($record.id)")
    } elseif (-not $SkipHashes) {
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $record.sha256) {
            $issues.Add("Source hash changed: $($record.id)")
        } else { $verifiedHashes++ }
    }
}
[pscustomobject]@{
    checked_at=[DateTimeOffset]::Now.ToString('o')
    status=$(if ($issues.Count -eq 0) {'PASS'} else {'FAIL'})
    markdown_files=$docs.Count
    local_links=$linkCount
    powershell_scripts=$scripts.Count
    indexed_sources=$index.Count
    source_hashes_checked=$verifiedHashes
    known_unavailable_sources=@($index | Where-Object {-not $_.available} | ForEach-Object id)
    issues=@($issues)
    scope='Offline documentation, syntax, and file integrity only; no network or physical model validation.'
} | ConvertTo-Json -Depth 5
if ($issues.Count -gt 0) { exit 1 }
