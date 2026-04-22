param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$envFile = Join-Path $repoRoot ".env"
$sqlclPath = "C:\Users\cvpow\Downloads\sqlcl-latest\sqlcl\bin\sql.exe"

if (-not (Test-Path $sqlclPath)) {
    throw "SQLcl not found at $sqlclPath"
}

if (-not (Test-Path $envFile)) {
    throw ".env not found at $envFile"
}

Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*$' -or $_ -match '^\s*#') {
        return
    }

    $parts = $_ -split '=', 2
    if ($parts.Length -ne 2) {
        return
    }

    $name = $parts[0].Trim()
    $value = $parts[1]

    if ($name -eq "ORACLE_CLIENT_LIB_DIR" -or $name -eq "TNS_ADMIN" -or $name -eq "JAVA_HOME") {
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

Write-Host "Starting SQLcl MCP with $sqlclPath"
& $sqlclPath -mcp
