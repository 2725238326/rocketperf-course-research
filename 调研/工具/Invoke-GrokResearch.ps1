param(
    [Parameter(Mandatory=$true)][string]$PromptFile,
    [Parameter(Mandatory=$true)][string]$OutputStem
)
$ErrorActionPreference = 'Stop'
$configPath = 'E:\Demo\IDEA_collector\apikey\grok.txt'
$configText = Get-Content -LiteralPath $configPath -Raw
$baseUrl = [regex]::Match($configText, 'https?://[^\s"''<>]+').Value.TrimEnd('/')
$apiKey = [regex]::Match($configText, '(?:sk-|xai-)[A-Za-z0-9_\-]+').Value
if (-not $baseUrl -or -not $apiKey) { throw 'Missing endpoint or key in local configuration.' }
$promptText = Get-Content -LiteralPath $PromptFile -Raw
$payload = @{
    model = 'grok-4.6'
    input = @(@{role='user'; content=$promptText})
    tools = @(@{type='web_search'})
    max_tool_calls = 7
    stream = $false
} | ConvertTo-Json -Depth 8
$response = Invoke-RestMethod -Uri ($baseUrl + '/v1/responses') -Method Post -Headers @{Authorization=('Bearer ' + $apiKey)} -ContentType 'application/json' -Body ([System.Text.Encoding]::UTF8.GetBytes($payload)) -TimeoutSec 240
$searchRecords = @($response.output | Where-Object type -eq 'web_search_call' | Select-Object status,action)
$messages = @($response.output | Where-Object type -eq 'message' | ForEach-Object { $_.content | Where-Object type -eq 'output_text' | ForEach-Object { $_.text } })
$record = [ordered]@{
    retrievedAt = (Get-Date).ToString('o')
    model = $response.model
    responseId = $response.id
    searchRecords = $searchRecords
    messages = $messages
    annotations = @($response.output | Where-Object type -eq 'message' | ForEach-Object { $_.content | ForEach-Object { $_.annotations } })
}
$outDirectory = Split-Path -Parent $OutputStem
if (-not (Test-Path -LiteralPath $outDirectory)) { New-Item -ItemType Directory -Path $outDirectory | Out-Null }
[System.IO.File]::WriteAllText(($OutputStem + '.json'), ($record | ConvertTo-Json -Depth 30), [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText(($OutputStem + '.md'), ($messages -join "`n`n"), [System.Text.UTF8Encoding]::new($false))
'Saved: ' + $OutputStem
'Search records: ' + $searchRecords.Count
$messages -join "`n`n"
