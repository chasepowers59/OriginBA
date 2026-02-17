param(
    [string]$JrsUrl = $env:JRS_URL,
    [string]$JrsUser = $env:JRS_USER,
    [string]$JrsPassword = $env:JRS_PASSWORD,
    [string]$ReportZip = $env:REPORT_ZIP,
    [string]$InputControlsPayload = $env:INPUT_CONTROLS_PAYLOAD
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($JrsUrl) -or [string]::IsNullOrWhiteSpace($JrsUser) -or [string]::IsNullOrWhiteSpace($JrsPassword)) {
    throw "Set JRS_URL, JRS_USER, and JRS_PASSWORD (env vars or parameters)."
}
if ([string]::IsNullOrWhiteSpace($ReportZip)) {
    throw "Set REPORT_ZIP to a report unit zip path."
}
if (-not (Test-Path $ReportZip)) {
    throw "Report package not found: $ReportZip"
}

$authBytes = [System.Text.Encoding]::UTF8.GetBytes("$JrsUser`:$JrsPassword")
$authHeader = "Basic " + [Convert]::ToBase64String($authBytes)
$headers = @{ Authorization = $authHeader }

$importUrl = "$JrsUrl/rest_v2/import?update=true"
Write-Output "Importing $ReportZip to $importUrl"
$resp = Invoke-WebRequest -Uri $importUrl -Method Post -Headers $headers -ContentType "application/zip" -InFile $ReportZip
$resp.Content | Out-File "$env:TEMP\jrs_import_response.json" -Encoding utf8
Write-Output "Import response saved: $env:TEMP\jrs_import_response.json"

if (-not [string]::IsNullOrWhiteSpace($InputControlsPayload) -and (Test-Path $InputControlsPayload)) {
    $payloadText = Get-Content $InputControlsPayload -Raw
    $payload = ConvertFrom-Json $payloadText
    if ($payload.uri) {
        $targetUri = "$JrsUrl/rest_v2/resources$($payload.uri).json"
        Write-Output "Applying input controls payload to $targetUri"
        Invoke-WebRequest -Uri $targetUri -Method Put -Headers $headers -ContentType "application/json" -Body $payloadText | Out-Null
    } else {
        Write-Output "Input controls payload has no .uri field, skipping PUT."
    }
}

Write-Output "Done. Example smoke render:"
Write-Output "$JrsUrl/rest_v2/reports/reports/origin/ops_hub_dashboard.pdf?START_TS=2026-01-01T00:00:00&END_TS=2026-01-31T23:59:59"
