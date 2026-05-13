# 仅启动本机 agent（端口 5004），连远端云控制面
#
# 用法：双击 scripts\start_local_agent.bat
# 或：powershell -ExecutionPolicy Bypass -File scripts\start_local_agent.ps1
#
# 改云端地址 / 密钥：编辑下面的 $env:MJQ_* 三行。

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot

function Resolve-Python {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Python not found"
}
$PythonExe = Resolve-Python

# ---- 环境变量（按需改）-------------------------------
$env:MJQ_CLOUD_URL = "http://81.69.16.235:8090"
$env:MJQ_JWT_SECRET = "2818e03ffbd8b02f84a04e7fa6d65b23c650e6d6c9b1c86ce6ce7a2abd1bbac0"
$env:MJQ_LOCAL_CORS_ORIGINS = "http://81.69.16.235:8090,http://localhost:5174,http://127.0.0.1:5174"

# ---- 端口检查 -----------------------------------------
$existing = Get-NetTCPConnection -LocalPort 5004 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    $procId = $existing[0].OwningProcess
    Write-Host "[!] 5004 已被 PID=$procId 占用" -ForegroundColor Yellow
    $reply = Read-Host "    杀掉再启? [y/N]"
    if ($reply -eq 'y' -or $reply -eq 'Y') {
        Stop-Process -Id $procId -Force
        Start-Sleep -Milliseconds 500
    } else {
        exit 1
    }
}

# ---- 看当前绑定 ---------------------------------------
Write-Host "=== 当前绑定 ===" -ForegroundColor Cyan
Set-Location $RootDir
& $PythonExe -m scripts.bind_user status

# ---- 启动 ---------------------------------------------
Write-Host ""
Write-Host "=== 启动本机 agent (port 5004) ===" -ForegroundColor Cyan
Write-Host "云端: $env:MJQ_CLOUD_URL"
Write-Host "Ctrl+C 停止"
Write-Host ""

& $PythonExe app.py
