@echo off
REM 双击启动本机 agent（连远端云）
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_local_agent.ps1"
pause
