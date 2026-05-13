# 知枢 · 本机 agent 首次安装向导
#
# 模式：
#   bundled —— 包里带 Python（python_embed/），用户无需任何 Python 安装
#   lite    —— 用包外系统 Python + 本地 .venv
# 自动检测 .bundled_python 标记选择模式。
#
# 流程：
#   1. 准备 Python（bundled 跳过；lite 检查系统 Python + 建 venv）
#   2. 装依赖（bundled 已预装；lite 跑 pip install）
#   3. 询问云端地址 / JWT 密钥 / 用户名
#   4. 写 config.ini + 调 bind_user
#   5. 自检 + 桌面快捷方式

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

# ─── 模式判断 ───────────────────────────────────────────
$BundledMarker = Join-Path $RootDir ".bundled_python"
$IsBundled = Test-Path $BundledMarker
$EmbedPy = Join-Path $RootDir "python_embed\python.exe"

if ($IsBundled -and (Test-Path $EmbedPy)) {
    Write-Host ""
    Write-Host "模式：bundled（内嵌 Python，无需系统 Python）" -ForegroundColor Green
    $TargetPy = $EmbedPy
} else {
    Write-Host ""
    Write-Host "模式：lite（用系统 Python + .venv）" -ForegroundColor Yellow

    # 1. 系统 Python 检查
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
        Write-Host "  请先安装 Python：https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "  或者跟管理员要 bundled 版安装包（内置 Python，无需安装）" -ForegroundColor Yellow
        Pause-Exit 1
    }

    # 2. venv
    Write-Host ""
    Write-Host "[2/5] 建 venv 装依赖..." -ForegroundColor Yellow
    $VenvDir = Join-Path $RootDir ".venv"
    if (-not (Test-Path $VenvDir)) {
        & $pythonCmd -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) { Pause-Exit 1 }
    }
    $TargetPy = Join-Path $VenvDir "Scripts\python.exe"
    & $TargetPy -m pip install --upgrade pip --quiet 2>&1 | Out-Null
    & $TargetPy -m pip install -r requirements.txt 2>&1 | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) { Pause-Exit 1 }
    Write-Host "  ✓ 依赖装好了" -ForegroundColor Green
}

# bundled 模式：跳过 1+2
if ($IsBundled) {
    Write-Host ""
    Write-Host "[1-2/5] 内嵌 Python 已就绪，跳过装依赖" -ForegroundColor Green
}

# ─── 3. 询问配置 ────────────────────────────────────────
Write-Host ""
Write-Host "[3/5] 配置云端连接..." -ForegroundColor Yellow

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
    Write-Host "  ✗ JWT 密钥不能为空" -ForegroundColor Red
    Pause-Exit 1
}
if ([string]::IsNullOrWhiteSpace($username)) {
    Write-Host "  ✗ 用户名不能为空" -ForegroundColor Red
    Pause-Exit 1
}

@(
    "# 知枢本机 agent 配置 —— 由 setup 生成，可以手工编辑后重启",
    "MJQ_CLOUD_URL=$cloudUrl",
    "MJQ_JWT_SECRET=$jwtSecret",
    "MJQ_LOCAL_CORS_ORIGINS=$cloudUrl,http://localhost:5174",
    "BOUND_USER=$username"
) | Set-Content -Path $ConfigFile -Encoding utf8
Write-Host "  ✓ 配置写入 $ConfigFile" -ForegroundColor Green

# ─── 4. 绑定 ────────────────────────────────────────────
Write-Host ""
Write-Host "[4/5] 绑定本机到云端用户 ‘$username’..." -ForegroundColor Yellow
& $TargetPy -m scripts.bind_user bind $username
if ($LASTEXITCODE -ne 0) { Pause-Exit 1 }

# ─── 5. 桌面快捷方式 ────────────────────────────────────
Write-Host ""
Write-Host "[5/5] 创建桌面快捷方式..." -ForegroundColor Yellow

$createShortcut = Read-Host "  是否在桌面创建 ‘知枢’ 图标? [Y/n]"
if ([string]::IsNullOrWhiteSpace($createShortcut) -or $createShortcut -eq 'y' -or $createShortcut -eq 'Y') {
    try {
        $desktop = [Environment]::GetFolderPath('Desktop')
        $shortcutPath = Join-Path $desktop "知枢.lnk"
        $startBat = Join-Path $RootDir "start.bat"

        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $startBat
        $shortcut.WorkingDirectory = $RootDir
        $shortcut.WindowStyle = 1
        $shortcut.Description = "知枢本机 agent ($username)"

        # 用 python 解释器作为图标（自带的）
        $pyForIcon = if ($IsBundled) { $EmbedPy } else { $TargetPy }
        if (Test-Path $pyForIcon) { $shortcut.IconLocation = "$pyForIcon,0" }

        $shortcut.Save()
        Write-Host "  ✓ 桌面已创建 ‘知枢’ 图标" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ 快捷方式创建失败：$_" -ForegroundColor Yellow
        Write-Host "    不致命；以后直接双击 start.bat 即可" -ForegroundColor Yellow
    }
} else {
    Write-Host "  跳过；以后直接双击 start.bat" -ForegroundColor Gray
}

# ─── 完成 ───────────────────────────────────────────────
Header "安装完成 ✓"
Write-Host ""
Write-Host "数据目录：    ~/.handynotes/$username/" -ForegroundColor White
Write-Host "云端：        $cloudUrl" -ForegroundColor White
Write-Host ""
Write-Host "日常使用：" -ForegroundColor Yellow
Write-Host "  ① 双击桌面 ‘知枢’ 图标 或 start.bat 启动" -ForegroundColor White
Write-Host "  ② 浏览器打开 $cloudUrl 登录" -ForegroundColor White
Write-Host ""
Write-Host "停止：       双击 stop.bat" -ForegroundColor White
Write-Host "重新配置：    再跑 setup.bat" -ForegroundColor White
Pause-Exit 0
