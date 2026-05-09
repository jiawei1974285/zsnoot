# 知枢 · 云本机分离模式 一键启动（P1-P5）
#
# 三个进程：
#   ① 云端控制面  (cloud/main.py, port 5005)
#   ② 本机 agent  (app.py,        port 5004)
#   ③ 前端 dev    (Vite,           port 5174)
#
# 用法：
#   双击 scripts\start_split.bat
#   或：powershell -ExecutionPolicy Bypass -File scripts\start_split.ps1 [-User <name>] [-Rebind]
#
# 首次：会问你「这台机器属于哪个云端用户」（绑定本机为该用户）。
# 之后：直接读 data/machine_binding.json，跳过提问。
# 切换：加 -Rebind 重新绑定。
#
# 停止：双击 scripts\stop_split.bat 或关掉三个弹出窗口。

param(
    [string]$User = "",
    [switch]$Rebind
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $RootDir "frontend"

# ---- Python 解析 ----
function Resolve-Python {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $bundled = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path $bundled) { return $bundled }
    throw "Python not found. Install Python or add it to PATH."
}
$PythonExe = Resolve-Python

Write-Host "=== mjq cloud-split start (P1-P5) ===" -ForegroundColor Cyan
Write-Host "Project root: $RootDir"
Write-Host ""

# ---- 1. 端口检查（5004 / 5005 / 5174）---------------------
function Test-Port($port, $label) {
    $existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($existing) {
        $procId = $existing[0].OwningProcess
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        Write-Host "[!] Port $port ($label) in use: PID=$procId Name=$($proc.ProcessName)" -ForegroundColor Yellow
        $reply = Read-Host "    Kill it and continue? [y/N]"
        if ($reply -eq 'y' -or $reply -eq 'Y') {
            Stop-Process -Id $procId -Force
            Start-Sleep -Milliseconds 500
            Write-Host "    Killed PID $procId" -ForegroundColor Green
        } else {
            Write-Host "    Aborting." -ForegroundColor Red
            exit 1
        }
    }
}
Test-Port 5004 "agent"
Test-Port 5005 "cloud"
Test-Port 5174 "frontend"

# ---- 2. 依赖检查 ----------------------------------------------
$NodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $NodeModules)) {
    Write-Host "[!] frontend/node_modules missing, running npm install..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "    npm install failed" -ForegroundColor Red; exit 1 }
    Pop-Location
}

$pythonOk = $false
try {
    & $PythonExe -c "import flask, yaml, requests, jwt, apscheduler" 2>$null
    if ($LASTEXITCODE -eq 0) { $pythonOk = $true }
} catch { }
if (-not $pythonOk) {
    Write-Host "[!] Python deps incomplete, running pip install -r requirements.txt..." -ForegroundColor Yellow
    Push-Location $RootDir
    & $PythonExe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "    pip install failed" -ForegroundColor Red; exit 1 }
    Pop-Location
}

# ---- 3. 确保前端 .env.local 配好分离模式 baseURL ----------
$EnvLocal = Join-Path $FrontendDir ".env.local"
if (-not (Test-Path $EnvLocal)) {
    Write-Host "[*] Writing frontend/.env.local for split mode..." -ForegroundColor Cyan
    @(
        "VITE_CLOUD_API=http://127.0.0.1:5005",
        "VITE_LOCAL_API=http://127.0.0.1:5004"
    ) | Set-Content -Path $EnvLocal -Encoding utf8
    Write-Host "    wrote $EnvLocal" -ForegroundColor Green
}

# ---- 4. 绑定本机到云端用户 -----------------------------------
$BindingFile = Join-Path $RootDir "data\machine_binding.json"
$NeedBind = $Rebind -or (-not (Test-Path $BindingFile))

if ($NeedBind) {
    if (-not $User) {
        Write-Host ""
        Write-Host "本机 agent 还未绑定到云端用户。" -ForegroundColor Yellow
        Write-Host "请输入将要使用本机的云端用户名（首次使用：填一个你想注册的 admin 用户名，"
        Write-Host "后续会在浏览器里完成 setup；之后用同一个用户名登录即可）。"
        $User = Read-Host "用户名"
    }
    if (-not $User) { Write-Host "用户名不能为空。Aborting." -ForegroundColor Red; exit 1 }
    Push-Location $RootDir
    & $PythonExe -m scripts.bind_user bind $User
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "bind failed" -ForegroundColor Red; exit 1 }
    Pop-Location
} else {
    # 显示当前绑定
    Push-Location $RootDir
    & $PythonExe -m scripts.bind_user status
    Pop-Location
}

# ---- 5. 启动云端（新窗口，端口 5005）------------------------
Write-Host ""
Write-Host "[*] Starting cloud control plane (port 5005)..." -ForegroundColor Cyan
$cloudCmd = "& { Set-Location '$RootDir'; `$Host.UI.RawUI.WindowTitle='mjq-cloud (5005)'; & '$PythonExe' -m cloud.main }"
Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $cloudCmd | Out-Null

# 等云端起来
Write-Host "[*] Waiting for cloud /api/cloud/health..." -ForegroundColor Cyan
$cloudReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:5005/api/cloud/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $cloudReady = $true; break }
    } catch { }
}
if (-not $cloudReady) { Write-Host "    cloud not ready in 30s; check the cloud window." -ForegroundColor Yellow }
else { Write-Host "    cloud is up." -ForegroundColor Green }

# ---- 6. 启动本机 agent（新窗口，端口 5004）------------------
Write-Host "[*] Starting local agent (port 5004)..." -ForegroundColor Cyan
$agentCmd = "& { Set-Location '$RootDir'; `$Host.UI.RawUI.WindowTitle='mjq-agent (5004)'; `$env:MJQ_CLOUD_URL='http://127.0.0.1:5005'; `$env:MJQ_LOCAL_CORS_ORIGINS='http://localhost:5174,http://127.0.0.1:5174'; & '$PythonExe' app.py }"
Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $agentCmd | Out-Null

# 等 agent 起来
Write-Host "[*] Waiting for agent /api/health..." -ForegroundColor Cyan
$agentReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:5004/api/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $agentReady = $true; break }
    } catch { }
}
if (-not $agentReady) { Write-Host "    agent not ready in 30s; check the agent window." -ForegroundColor Yellow }
else { Write-Host "    agent is up." -ForegroundColor Green }

# ---- 7. 启动前端 dev（新窗口，端口 5174）-------------------
Write-Host "[*] Starting frontend Vite (port 5174)..." -ForegroundColor Cyan
$frontendCmd = "& { Set-Location '$FrontendDir'; `$Host.UI.RawUI.WindowTitle='mjq-frontend (5174)'; npm.cmd run dev }"
Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $frontendCmd | Out-Null

# ---- 8. 输出指引 ---------------------------------------------
Write-Host ""
Write-Host "=== Started ===" -ForegroundColor Green
Write-Host "  Frontend     : http://localhost:5174  (open this)" -ForegroundColor White
Write-Host "  Cloud API    : http://localhost:5005  (admin / auth / schema)" -ForegroundColor White
Write-Host "  Agent API    : http://localhost:5004  (your data; bound to user)" -ForegroundColor White
Write-Host ""
Write-Host "First time? In the browser:"
Write-Host "  1) Setup admin (用同一个用户名: 与刚才输入的绑定用户名一致)"
Write-Host "  2) Setup 时选择一个 schema 模板（5 选 1）"
Write-Host "  3) 之后随手记 / 上传材料 / 自动入库都在 ~/.handynotes/<username>/"
Write-Host ""
Write-Host "Logs:"
Write-Host "  agent : ~/.handynotes/<username>/mjq.log"
Write-Host "  cloud : (cloud window stdout)"
Write-Host ""
Write-Host "Stop: double-click scripts\stop_split.bat or close all 3 windows."
