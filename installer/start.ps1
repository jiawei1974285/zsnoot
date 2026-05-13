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

# 选 Python：优先内嵌；其次 .venv
$EmbedPy = Join-Path $RootDir "python_embed\python.exe"
$VenvPy = Join-Path $RootDir ".venv\Scripts\python.exe"
if (Test-Path $EmbedPy) {
    $TargetPy = $EmbedPy
    $modeLabel = "内嵌 Python"
} elseif (Test-Path $VenvPy) {
    $TargetPy = $VenvPy
    $modeLabel = ".venv"
} else {
    Write-Host "✗ 找不到 Python（python_embed/ 和 .venv 都不存在）" -ForegroundColor Red
    Write-Host "  请先跑 setup.bat" -ForegroundColor Yellow
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
Write-Host "  Python：   $modeLabel" -ForegroundColor White
Write-Host "  监听：     http://localhost:5004" -ForegroundColor White
Write-Host ""
Write-Host "  浏览器 5 秒后自动打开 http://localhost:5004" -ForegroundColor Yellow
Write-Host "  关闭此窗口 = 停止本机 agent" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# 后台等 agent 起来，自动开浏览器
$browserJob = Start-Job -ScriptBlock {
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5004/api/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                Start-Sleep -Seconds 1
                Start-Process "http://localhost:5004"
                return
            }
        } catch { }
    }
}

$Host.UI.RawUI.WindowTitle = "知枢 agent ($env:BOUND_USER)"
# 内嵌 Python 双保险：把安装根目录加进 PYTHONPATH，确保 scripts/* cloud/* 可被 import
$env:PYTHONPATH = $RootDir
& $TargetPy app.py

# agent 退出后清理浏览器自动打开任务
Stop-Job $browserJob -ErrorAction SilentlyContinue | Out-Null
Remove-Job $browserJob -Force -ErrorAction SilentlyContinue | Out-Null
