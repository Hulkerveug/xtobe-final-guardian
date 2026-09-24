param([switch]$WorkerOnly, [switch]$ServerOnly)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $ProjectRoot '.env'
if (Test-Path -LiteralPath $EnvFile) {
    Get-Content -LiteralPath $EnvFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
        $parts = $_ -split '=', 2
        if ($parts.Count -eq 2) {
            [Environment]::SetEnvironmentVariable(
                $parts[0].Trim(), $parts[1].Trim().Trim('"').Trim("'"), 'Process'
            )
        }
    }
}
if (-not $env:WHATSAPP_APP_SECRET -or -not $env:WHATSAPP_VERIFY_TOKEN) {
    throw 'WhatsApp secrets are missing from the local .env file.'
}
$Python = Get-Command py -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $Python) { throw 'Python 3.11 or newer is required.' }
$LogDir = Join-Path $ProjectRoot 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Processes = @()
try {
    if (-not $WorkerOnly) {
        $Processes += Start-Process $Python.Source -ArgumentList @('-u', (Join-Path $ProjectRoot 'connector\bridge_server.py')) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $LogDir 'connector-server.log') -RedirectStandardError (Join-Path $LogDir 'connector-server-error.log')
    }
    if (-not $ServerOnly) {
        $Processes += Start-Process $Python.Source -ArgumentList @('-u', (Join-Path $ProjectRoot 'connector\worker.py')) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $LogDir 'connector-worker.log') -RedirectStandardError (Join-Path $LogDir 'connector-worker-error.log')
    }
    Write-Host 'Xtobe WhatsApp bridge started on loopback; credentials were not logged.'
    $Processes | Wait-Process
} finally {
    foreach ($Process in $Processes) {
        if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -Force }
    }
}
