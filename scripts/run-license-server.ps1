# Production runner for Windows: loads private .env, logs output, and restarts the server.
$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\Users\Nishan\Xtobe\xtobe-final-guardian"
$Python = "C:\Users\Nishan\AppData\Local\Programs\Python\Python312\python.exe"
$LogDir = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDir "license_server.log"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $kv = $_ -split '=', 2
    if ($kv.Count -eq 2) {
      [Environment]::SetEnvironmentVariable($kv[0].Trim(), $kv[1].Trim().Trim('"').Trim("'"), "Process")
    }
  }
  Write-Host "Loaded .env"
}
if (-not $env:XTOBE_LICENSE_DB) {
  $env:XTOBE_LICENSE_DB = "C:\secure\licenses.json"
  New-Item -ItemType Directory -Force -Path "C:\secure" | Out-Null
}
Write-Host "Starting license_server.py; logs: $LogFile"
while ($true) {
  "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Starting server" | Out-File -Append $LogFile
  & $Python (Join-Path $ProjectRoot "server\license_server.py") 2>&1 | Tee-Object -FilePath $LogFile -Append
  "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Server stopped; restarting in 5 seconds" | Out-File -Append $LogFile
  Start-Sleep -Seconds 5
}
