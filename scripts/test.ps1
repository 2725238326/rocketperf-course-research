param([ValidateSet('Debug','Release')][string]$Configuration='Debug',[string]$Python='python',[switch]$Sanitize,[string]$Compiler='gcc')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$arguments=@((Join-Path $root 'tools/pipeline.py'),'test','--configuration',$Configuration,'--compiler',$Compiler)
if($Sanitize){$arguments+='--sanitize'}
& $Python @arguments
if($LASTEXITCODE -ne 0){throw 'Tests failed; the current test report records failure.'}
