@echo off
REM 双击启动云本机分离模式（cloud 5005 + agent 5004 + frontend 5174）
REM 可传一个参数指定绑定用户名: scripts\start_split.bat alice
cd /d "%~dp0\.."
if "%~1"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_split.ps1"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_split.ps1" -User %1
)
pause
