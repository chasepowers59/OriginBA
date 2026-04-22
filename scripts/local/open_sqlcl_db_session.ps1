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

$config = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*$' -or $_ -match '^\s*#') {
        return
    }

    $parts = $_ -split '=', 2
    if ($parts.Length -ne 2) {
        return
    }

    $config[$parts[0].Trim()] = $parts[1]
}

$dbUser = $config["DB_USER"]
$dbPassword = $config["DB_PASSWORD"]
$dbConnectString = $config["DB_CONNECT_STRING"]

if (-not $dbConnectString) {
    $dbHost = $config["DB_HOST"]
    $dbPort = $config["DB_PORT"]
    $dbServiceName = $config["DB_SERVICE_NAME"]
    if ($dbHost -and $dbPort -and $dbServiceName) {
        $dbConnectString = "$dbHost`:$dbPort/$dbServiceName"
    }
}

if (-not $dbUser -or -not $dbPassword -or -not $dbConnectString) {
    throw "DB_USER, DB_PASSWORD, and DB_CONNECT_STRING or DB_HOST/DB_PORT/DB_SERVICE_NAME must be present in .env"
}

if ($config.ContainsKey("ORACLE_CLIENT_LIB_DIR")) {
    [Environment]::SetEnvironmentVariable("ORACLE_CLIENT_LIB_DIR", $config["ORACLE_CLIENT_LIB_DIR"], "Process")
}

if ($config.ContainsKey("TNS_ADMIN")) {
    [Environment]::SetEnvironmentVariable("TNS_ADMIN", $config["TNS_ADMIN"], "Process")
}

if ($config.ContainsKey("JAVA_HOME")) {
    [Environment]::SetEnvironmentVariable("JAVA_HOME", $config["JAVA_HOME"], "Process")
}

$connectString = "$dbUser/$dbPassword@$dbConnectString"
Write-Host "Opening SQLcl session for $dbUser@$dbConnectString"
& $sqlclPath $connectString
