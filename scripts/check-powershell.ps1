$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$issues=@()
$scripts=@(Get-ChildItem -LiteralPath (Join-Path $root 'scripts'),(Join-Path $root '调研/scripts'),(Join-Path $root '调研/工具') -Filter '*.ps1' -Recurse -File)
foreach($script in $scripts){
    $tokens=$null; $parseErrors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($script.FullName,[ref]$tokens,[ref]$parseErrors)
    foreach($problem in $parseErrors){$issues+=($script.Name+': '+$problem.Message)}
}
[pscustomobject]@{scripts=$scripts.Count;issues=$issues}|ConvertTo-Json -Depth 3
if($issues.Count){exit 1}
