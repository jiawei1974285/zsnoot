# 分离开发模式：本机 agent (5004) + 前端 dev (5174)，云端用远程已部署的
#
# 与 start_split.ps1 的区别：那个还要在本机启 cloud；这个直接用远端云。
# 适合：日常开发，频繁改前端代码热重载；agent 改了重启 5004 即可。
#
# 用法：双击 scripts\start_local_dev.bat
#       或 powershell -ExecutionPolicy Bypass -File scripts\start_local_dev.ps1
#
# 改云端地址 / 密钥：编辑下面 $env:MJQ_* 三行。

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $RootDir "frontend"

function Resolve-Python {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Python not found"
}
$PythonExe = Resolve-Python

# ---- 远端云端配置（按需改）------------------------------
$CloudUrl    = "http://81.69.16.235:8090"
$JwtSecret   = "2818e03ffbd8b02f84a04e7fa6d65b23c650e6d6c9b1c86ce6ce7a2abd1bbac0"
$LocalOrigins = "http://81.69.16.235:8090,http://localhost:5174,http://127.0.0.1:5174"

Write-Host "=== 分离开发启动 ===" -ForegroundColor Cyan
Write-Host "  云端：$CloudUrl（远端，已部署）"
Write-Host "  本机 agent：127.0.0.1:5004"
Write-Host "  前端 dev：http://localhost:5174"
Write-Host ""

# ---- 端口检查 -------------------------------------------
function Test-Port($port, $label) {
    $existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($existing) {
        $procId = $existing[0].OwningProcess
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        Write-Host "[!] $label 端口 $port 被 PID=$procId ($($proc.ProcessName)) 占用" -ForegroundColor Yellow
        $reply = Read-Host "    杀掉再启? [y/N]"
        if ($reply -eq 'y' -or $reply -eq 'Y') {
            Stop-Process -Id $procId -Force
            Start-Sleep -Milliseconds 500
        } else {
            exit 1
        }
    }
}
Test-Port 5004 "agent"
Test-Port 5174 "frontend"

# ---- 确认前端 .env.local 指向远端云 --------------------
$EnvLocal = Join-Path $FrontendDir ".env.local"
$needWrite = $true
if (Test-Path $EnvLocal) {
    $content = Get-Content $EnvLocal -Raw
    if ($content -match [regex]::Escape($CloudUrl)) { $needWrite = $false }
}
if ($needWrite) {
    Write-Host "[*] 写 frontend/.env.local (VITE_CLOUD_API → $CloudUrl)" -ForegroundColor Cyan
    @(
        "VITE_CLOUD_API=$CloudUrl",
        "VITE_LOCAL_API=http://127.0.0.1:5004"
    ) | Set-Content -Path $EnvLocal -Encoding utf8
}

# ---- 看当前绑定 -----------------------------------------
Write-Host "=== 当前本机绑定 ===" -ForegroundColor Cyan
Set-Location $RootDir
& $PythonExe -m scripts.bind_user status
Write-Host ""

# ---- 启动 agent（新窗口）-------------------------------
Write-Host "[*] 启动本机 agent (5004)..." -ForegroundColor Cyan
$agentCmd = "& { Set-Location '$RootDir'; `$Host.UI.RawUI.WindowTitle='mjq-agent (5004)'; `$env:MJQ_CLOUD_URL='$CloudUrl'; `$env:MJQ_JWT_SECRET='$JwtSecret'; `$env:MJQ_LOCAL_CORS_ORIGINS='$LocalOrigins'; & '$PythonExe' app.py }"
Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $agentCmd | Out-Null

# 等 agent 起来
$agentReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:5004/api/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $agentReady = $true; break }
    } catch { }
}
if ($agentReady) { Write-Host "    agent 已启动" -ForegroundColor Green }
else { Write-Host "    agent 30s 未起来，看 agent 窗口" -ForegroundColor Yellow }

# ---- 启动前端 dev（新窗口）----------------------------
Write-Host "[*] 启动前端 dev (5174)..." -ForegroundColor Cyan
$frontCmd = "& { Set-Location '$FrontendDir'; `$Host.UI.RawUI.WindowTitle='mjq-frontend (5174)'; npm.cmd run dev }"
Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $frontCmd | Out-Null

# ---- 提示 -----------------------------------------------
Write-Host ""
Write-Host "=== 已启动 ===" -ForegroundColor Green
Write-Host "  浏览器开： http://localhost:5174 （dev，热重载）"
Write-Host "  或直连云端浏览： $CloudUrl"
Write-Host ""
Write-Host "  agent 窗口：mjq-agent (5004)"
Write-Host "  前端窗口：mjq-frontend (5174)"
Write-Host ""
Write-Host "停止：scripts\stop_split.bat 或关掉两个弹窗。"
