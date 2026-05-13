@echo off
REM 分离开发模式：本机 agent + 前端 dev，云端用远程已部署的
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_local_dev.ps1"
pause
