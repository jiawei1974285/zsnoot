# 知枢 · 本机 agent 日常启动（读 config.ini）

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

function Pause-Exit($code = 0) {
    Write-Host ""
    Read-Host "按回车键关闭"
    exit $code
}

# 读 config.ini
$ConfigFile = Join-Path $RootDir "config.ini"
if (-not (Test-Path $ConfigFile)) {
    Write-Host "✗ 找不到 config.ini，请先双击 setup.bat 完成首次配置" -ForegroundColor Red
    Pause-Exit 1
}

Get-Content $ConfigFile | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.+?)\s*$') {
        Set-Item "env:$($Matches[1])" $Matches[2]
    }
}

if (-not $env:MJQ_JWT_SECRET) {
    Write-Host "✗ config.ini 缺 MJQ_JWT_SECRET" -ForegroundColor Red
    Pause-Exit 1
}

# 找 venv
$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "✗ 没找到 .venv，请先跑 setup.bat" -ForegroundColor Red
    Pause-Exit 1
}

# 端口检查
$existing = Get-NetTCPConnection -LocalPort 5004 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    $procId = $existing[0].OwningProcess
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    Write-Host "[!] 端口 5004 已被 PID=$procId ($($proc.ProcessName)) 占用" -ForegroundColor Yellow
    $reply = Read-Host "    杀掉再启? [y/N]"
    if ($reply -eq 'y' -or $reply -eq 'Y') {
        Stop-Process -Id $procId -Force
        Start-Sleep -Milliseconds 500
    } else {
        Pause-Exit 1
    }
}

Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  知枢 · 本机 agent" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  云端：     $env:MJQ_CLOUD_URL" -ForegroundColor White
Write-Host "  绑定用户： $env:BOUND_USER" -ForegroundColor White
Write-Host "  监听：     http://127.0.0.1:5004" -ForegroundColor White
Write-Host ""
Write-Host "  浏览器打开 $env:MJQ_CLOUD_URL 即可使用"
Write-Host "  Ctrl+C 停止" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$Host.UI.RawUI.WindowTitle = "知枢 agent ($env:BOUND_USER)"
& $VenvPython app.py
