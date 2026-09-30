param([string]$Case='cases/benchmarks/air_mach2_vacuum.ini',[ValidateSet('Debug','Release')][string]$Configuration='Release',[string]$RunId,[switch]$NoBuild,[string]$Python='python')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$arguments=@((Join-Path $root 'tools/pipeline.py'),'run','--case',$Case,'--configuration',$Configuration)
if($RunId){$arguments+=@('--run-id',$RunId)}
if($NoBuild){$arguments+='--no-build'}
& $Python @arguments
if($LASTEXITCODE -ne 0){throw 'Case failed; any reserved run retains a failure manifest.'}
