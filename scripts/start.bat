@echo off
REM 双击启动脚本：调用 start.ps1。Windows 默认 ExecutionPolicy 可能阻止脚本，用 Bypass 跑一次。
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
