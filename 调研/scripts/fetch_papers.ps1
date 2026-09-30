$ErrorActionPreference = 'Stop'
$outDir = Join-Path (Split-Path -Parent $PSScriptRoot) '文献'
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
$papers = @(
    @{Id='L01_CEA_Analysis_1994'; Url='https://ntrs.nasa.gov/api/citations/19950013764/downloads/19950013764.pdf'},
    @{Id='L02_CEA_Manual_1996'; Url='https://ntrs.nasa.gov/api/citations/19960044559/downloads/19960044559.pdf'},
    @{Id='L03_Throttling_Review_2009'; Url='https://ntrs.nasa.gov/api/citations/20090037061/downloads/20090037061.pdf'},
    @{Id='L04_LUMEN_Validation_2025'; Url='https://www.eucass.eu/doi/EUCASS2025-105.pdf'},
    @{Id='L05_LUMEN_Turbopump_2023'; Url='https://elib.dlr.de/195494/1/OS1-2-02_%20Parametric%20Optimization%20of%20Turbopump%20for%20Reusable%20Rocket%20Engine%20(RRE)%20Applications%20Mateusz%20Gulczynski.pdf'}
)
$papers | ForEach-Object -Parallel {
    $paper = $_
    $path = Join-Path $using:outDir ($paper.Id + '.pdf')
    if (Test-Path -LiteralPath $path) { [pscustomobject]@{Id=$paper.Id;Status='exists'}; return }
    try {
        Invoke-WebRequest -Uri $paper.Url -OutFile $path -TimeoutSec 90
        [pscustomobject]@{Id=$paper.Id;Status='downloaded';Bytes=(Get-Item -LiteralPath $path).Length}
    } catch { [pscustomobject]@{Id=$paper.Id;Status='error';Error=$_.Exception.Message} }
} -ThrottleLimit 5 | ForEach-Object { $_ | ConvertTo-Json -Compress }
