param(
    [string]$Sql,
    [string]$File,
    [ValidateSet("table", "json")]
    [string]$Format = "table"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pythonExe = Join-Path $repoRoot "venv\Scripts\python.exe"
$scriptPath = Join-Path $repoRoot "scripts\local\run_oracle_sql.py"

if (-not (Test-Path $pythonExe)) {
    throw "Python venv not found at $pythonExe"
}

if (-not (Test-Path $scriptPath)) {
    throw "Runner script not found at $scriptPath"
}

$argsList = @($scriptPath, "--format", $Format)
if ($Sql) {
    $argsList += @("--sql", $Sql)
}
if ($File) {
    $argsList += @("--file", $File)
}

& $pythonExe @argsList
