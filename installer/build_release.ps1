# 打包本机 agent 一键安装版
# 输出：dist/zsnoot-agent-v1.0/  + dist/zsnoot-agent-v1.0.zip
#
# 给最终用户的 zip 不含：
#   - .git, .venv, node_modules, frontend/, deploy/, tests/, cloud-demo/
#   - wiki/, raw/, data/, embeddings/（用户数据，运行时生成）
#   - .env（凭据；用户自己填）
#
# 给最终用户的 zip 包含：
#   - 所有 *.py 源码（agent 必需）
#   - cloud/ （仅 jwt_utils 与共享代码；不到 50KB）
#   - scripts/bind_user.py + __init__.py
#   - requirements.txt
#   - installer/* 摊在根（setup.bat / start.bat / stop.bat / README.txt）

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DistDir = Join-Path $RootDir "dist"
$Version = "v1.0.0"
$Name = "zsnoot-agent-$Version"
$OutDir = Join-Path $DistDir $Name
$ZipFile = Join-Path $DistDir "$Name.zip"

Set-Location $RootDir

Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  打包知枢本机 agent $Version" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan

# ─── 清旧产物 ───
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
if (Test-Path $ZipFile) { Remove-Item -Force $ZipFile }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# ─── 复制源码 ───
Write-Host "[*] 复制 Python 源码..." -ForegroundColor Yellow
$pyFiles = @(
    "app.py",
    "activity_log.py",
    "agent_bootstrap.py",
    "agent_status.py",
    "auth.py",
    "auto_ingest.py",
    "config_store.py",
    "file_parser.py",
    "file_watcher.py",
    "graph.py",
    "heartbeat.py",
    "ingest_batches.py",
    "ingest_service.py",
    "llm_client.py",
    "llm_tester.py",
    "mjq_logging.py",
    "note_intake.py",
    "orphan_detector.py",
    "scheduler.py",
    "schema_runtime.py",
    "user_data.py",
    "wiki_links.py",
    "requirements.txt"
)
foreach ($f in $pyFiles) {
    if (Test-Path (Join-Path $RootDir $f)) {
        Copy-Item (Join-Path $RootDir $f) (Join-Path $OutDir $f)
    } else {
        Write-Host "  ! 缺文件：$f" -ForegroundColor Yellow
    }
}

# ─── 复制 cloud/（agent 用 jwt_utils）───
Write-Host "[*] 复制 cloud/..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "cloud") | Out-Null
foreach ($f in @("__init__.py", "jwt_utils.py")) {
    $src = Join-Path $RootDir "cloud\$f"
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $OutDir "cloud\$f")
    }
}

# ─── 复制 scripts/ ───
Write-Host "[*] 复制 scripts/..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "scripts") | Out-Null
foreach ($f in @("__init__.py", "bind_user.py")) {
    Copy-Item (Join-Path $RootDir "scripts\$f") (Join-Path $OutDir "scripts\$f")
}

# ─── 复制 templates/（Flask render_template 用，可选）───
if (Test-Path (Join-Path $RootDir "templates")) {
    Copy-Item -Recurse (Join-Path $RootDir "templates") (Join-Path $OutDir "templates")
}

# ─── 复制 wiki/templates/（auto_ingest 兜底用）───
if (Test-Path (Join-Path $RootDir "wiki\templates")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "wiki\templates") | Out-Null
    Copy-Item -Recurse (Join-Path $RootDir "wiki\templates\*") (Join-Path $OutDir "wiki\templates\")
}

# ─── 把 installer/* 摊在根 ───
Write-Host "[*] 复制 installer 脚本到包根..." -ForegroundColor Yellow
foreach ($f in @("setup.bat", "setup.ps1", "start.bat", "start.ps1", "stop.bat", "stop.ps1", "README.txt")) {
    Copy-Item (Join-Path $PSScriptRoot $f) (Join-Path $OutDir $f)
}

# ─── 复制可选文档 ───
foreach ($f in @("schema.md", "purpose.md")) {
    if (Test-Path (Join-Path $RootDir $f)) {
        Copy-Item (Join-Path $RootDir $f) (Join-Path $OutDir $f)
    }
}

# ─── 打 zip ───
Write-Host "[*] 打 zip..." -ForegroundColor Yellow
Compress-Archive -Path "$OutDir\*" -DestinationPath $ZipFile -CompressionLevel Optimal

$zipSize = [math]::Round((Get-Item $ZipFile).Length / 1KB, 1)
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  打包完成 ✓" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  解压目录： $OutDir"
Write-Host "  Zip 文件： $ZipFile ($zipSize KB)"
Write-Host ""
Write-Host "  发给用户：把 zip 给他们，告诉他们解压后双击 setup.bat" -ForegroundColor White
Write-Host ""
