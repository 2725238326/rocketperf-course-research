param([ValidateSet('Debug','Release')][string]$Configuration='Debug',[string]$Compiler='gcc',[switch]$Sanitize,[string]$Python='python')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$arguments=@((Join-Path $root 'tools/pipeline.py'),'build','--configuration',$Configuration,'--compiler',$Compiler)
if($Sanitize){$arguments+='--sanitize'}
& $Python @arguments
if($LASTEXITCODE -ne 0){throw 'Build failed; inspect the latest build manifest and logs.'}
