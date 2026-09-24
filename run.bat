@echo off
REM Xtobe Final Guardian - launcher
REM Autostart: Win+R -> shell:startup -> drop a shortcut to this file there.
cd /d %~dp0
where py >nul 2>nul && (py guardian-core\app.py %*) || (python guardian-core\app.py %*)
