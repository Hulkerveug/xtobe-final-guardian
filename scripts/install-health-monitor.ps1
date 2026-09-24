# Installs the license health monitor as a SYSTEM startup task. Run elevated.
$TaskName = "XTOBE-Health-Monitor"
$ProjectRoot = "C:\Users\Nishan\Xtobe\xtobe-final-guardian"
$Script = Join-Path $ProjectRoot "scripts\health-monitor.py"
$Python = "C:\Users\Nishan\AppData\Local\Programs\Python\Python312\python.exe"
$Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Script`""
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Task $TaskName installed and started."
