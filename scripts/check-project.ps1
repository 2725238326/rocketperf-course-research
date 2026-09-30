param([switch]$SkipHashes,[string]$Python='python')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$arguments=@((Join-Path $root 'tools/project.py'),'check')
if($SkipHashes){$arguments+='--skip-hashes'}
& $Python @arguments
if($LASTEXITCODE -ne 0){throw 'Project governance checks failed.'}
