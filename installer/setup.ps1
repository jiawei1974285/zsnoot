# 知枢 · 本机 agent 首次安装向导
#
# 流程：
#   1. 检查 Python ≥ 3.10
#   2. 创建独立 venv 装依赖
#   3. 询问三件事：云端地址 / JWT 密钥 / 你的用户名
#   4. 写 config.ini，调 bind_user 完成本机绑定
#   5. 提示完成；之后双击 start.bat 即可日常使用

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

function Header($text) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
}

function Pause-Exit($code = 0) {
    Write-Host ""
    Read-Host "按回车键关闭"
    exit $code
}

Header "知枢 · 本机 agent 安装向导"

# ─── 1. Python 检查 ─────────────────────────────────────
Write-Host ""
Write-Host "[1/5] 检查 Python..." -ForegroundColor Yellow

$pythonCmd = $null
foreach ($candidate in @("python", "python3", "py")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $ver = & $cmd.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($ver -and [version]$ver -ge [version]"3.10") {
                $pythonCmd = $cmd.Source
                Write-Host "  ✓ 找到 Python $ver ($pythonCmd)" -ForegroundColor Green
                break
            }
        } catch { }
    }
}

if (-not $pythonCmd) {
    Write-Host "  ✗ 没找到 Python ≥ 3.10" -ForegroundColor Red
    Write-Host ""
    Write-Host "  请先安装 Python：" -ForegroundColor Yellow
    Write-Host "    1) 打开 https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "    2) 下载 Python 3.11 或 3.12" -ForegroundColor White
    Write-Host "    3) 安装时勾选 [Add Python to PATH]" -ForegroundColor White
    Write-Host "    4) 安装完后重新双击 setup.bat" -ForegroundColor White
    Pause-Exit 1
}

# ─── 2. 创建 venv + 装依赖 ──────────────────────────────
Write-Host ""
Write-Host "[2/5] 准备 Python 虚拟环境..." -ForegroundColor Yellow

$VenvDir = Join-Path $RootDir ".venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "  创建 .venv（一次性，约 30 秒）..." -ForegroundColor White
    & $pythonCmd -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ venv 创建失败" -ForegroundColor Red
        Pause-Exit 1
    }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "  ✗ venv Python 不存在：$VenvPython" -ForegroundColor Red
    Pause-Exit 1
}

Write-Host "  安装依赖（约 1-3 分钟，首次会下载较多）..." -ForegroundColor White
& $VenvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null
& $VenvPython -m pip install -r requirements.txt 2>&1 | Select-Object -Last 3
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ pip install 失败；请检查网络" -ForegroundColor Red
    Pause-Exit 1
}
Write-Host "  ✓ 依赖装好了" -ForegroundColor Green

# ─── 3. 询问配置 ────────────────────────────────────────
Write-Host ""
Write-Host "[3/5] 配置云端连接..." -ForegroundColor Yellow

# 读已有 config.ini（如果二次跑 setup）
$ConfigFile = Join-Path $RootDir "config.ini"
$existing = @{}
if (Test-Path $ConfigFile) {
    Get-Content $ConfigFile | ForEach-Object {
        if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.+?)\s*$') {
            $existing[$Matches[1]] = $Matches[2]
        }
    }
    Write-Host "  检测到已有 config.ini；留空回车将沿用旧值" -ForegroundColor White
}

function Prompt-With-Default($label, $key, $default) {
    $oldVal = if ($existing.ContainsKey($key)) { $existing[$key] } else { $default }
    $promptText = if ($oldVal) { "$label [当前 / 默认: $oldVal]" } else { $label }
    $input = Read-Host $promptText
    if ([string]::IsNullOrWhiteSpace($input)) { return $oldVal }
    return $input.Trim()
}

Write-Host ""
$cloudUrl = Prompt-With-Default "云端地址（例：http://81.69.16.235:8090）" "MJQ_CLOUD_URL" "http://127.0.0.1:5005"
$jwtSecret = Prompt-With-Default "JWT 密钥（从管理员处获取，64 位 hex）" "MJQ_JWT_SECRET" ""
$username = Prompt-With-Default "你的云端用户名（要与浏览器登录的一致）" "BOUND_USER" ""

if ([string]::IsNullOrWhiteSpace($jwtSecret)) {
    Write-Host "  ✗ JWT 密钥不能为空。请向管理员索取。" -ForegroundColor Red
    Pause-Exit 1
}
if ([string]::IsNullOrWhiteSpace($username)) {
    Write-Host "  ✗ 用户名不能为空。" -ForegroundColor Red
    Pause-Exit 1
}

# 写 config.ini
@(
    "# 知枢本机 agent 配置 —— 由 setup 生成，可以手工编辑后重启",
    "MJQ_CLOUD_URL=$cloudUrl",
    "MJQ_JWT_SECRET=$jwtSecret",
    "MJQ_LOCAL_CORS_ORIGINS=$cloudUrl,http://localhost:5174",
    "BOUND_USER=$username"
) | Set-Content -Path $ConfigFile -Encoding utf8
Write-Host "  ✓ 配置写入 $ConfigFile" -ForegroundColor Green

# ─── 4. 绑定本机 ────────────────────────────────────────
Write-Host ""
Write-Host "[4/5] 绑定本机到云端用户 ‘$username’..." -ForegroundColor Yellow
& $VenvPython -m scripts.bind_user bind $username
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ 绑定失败" -ForegroundColor Red
    Pause-Exit 1
}

# ─── 5. 自检 + 完成 ────────────────────────────────────
Write-Host ""
Write-Host "[5/5] 启动一次自检（10 秒）..." -ForegroundColor Yellow

$env:MJQ_CLOUD_URL = $cloudUrl
$env:MJQ_JWT_SECRET = $jwtSecret
$env:MJQ_LOCAL_CORS_ORIGINS = "$cloudUrl,http://localhost:5174"

$selfTestJob = Start-Job -ScriptBlock {
    param($py, $root)
    Set-Location $root
    & $py app.py 2>&1
} -ArgumentList $VenvPython, $RootDir

$started = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5004/api/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $started = $true; break }
    } catch { }
}

Stop-Job $selfTestJob -ErrorAction SilentlyContinue | Out-Null
Remove-Job $selfTestJob -Force -ErrorAction SilentlyContinue | Out-Null
# 杀掉自检留下的 python 进程
Get-NetTCPConnection -LocalPort 5004 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}

if ($started) {
    Write-Host "  ✓ 自检通过" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 自检未在 20s 内启动；不致命，但建议看 start.bat 输出" -ForegroundColor Yellow
}

# ─── 完成 ───────────────────────────────────────────────
Header "安装完成 ✓"
Write-Host ""
Write-Host "数据目录：    ~/.handynotes/$username/" -ForegroundColor White
Write-Host "云端：        $cloudUrl" -ForegroundColor White
Write-Host ""
Write-Host "日常使用：" -ForegroundColor Yellow
Write-Host "  1. 双击 start.bat 启动本机 agent" -ForegroundColor White
Write-Host "  2. 浏览器打开 $cloudUrl 登录" -ForegroundColor White
Write-Host ""
Write-Host "停止 agent：  双击 stop.bat" -ForegroundColor White
Write-Host "重新配置：    再跑一次 setup.bat" -ForegroundColor White
Pause-Exit 0
