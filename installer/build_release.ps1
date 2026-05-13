# 打包本机 agent 一键安装版（含内嵌 Python）
#
# 默认模式：bundled —— 把 Python 3.11 嵌入式发行版 + 所有 deps 装进包，
# 用户机器无需任何 Python 安装。代价：包从 120 KB 涨到 ~150 MB。
#
# 想出"轻量版"包（要求用户自带 Python）：加 -Lite 参数。
#
# 用法：
#   .\installer\build_release.ps1            # 默认 bundled
#   .\installer\build_release.ps1 -Lite      # 轻量
#
# 输出：dist/zsnoot-agent-v1.0.0.zip

param(
    [switch]$Lite,
    [string]$PresetCloudUrl = "",
    [string]$PresetJwt = ""
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DistDir = Join-Path $RootDir "dist"
$CacheDir = Join-Path $RootDir ".build_cache"
$Version = "v1.0.0"
$Mode = if ($Lite) { "lite" } else { "bundled" }
$Name = "zsnoot-agent-$Version-$Mode"
$OutDir = Join-Path $DistDir $Name
$ZipFile = Join-Path $DistDir "$Name.zip"

$EmbedVersion = "3.11.9"
$EmbedUrl = "https://www.python.org/ftp/python/$EmbedVersion/python-$EmbedVersion-embed-amd64.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"

Set-Location $RootDir

Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  打包知枢本机 agent $Version  ($Mode)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan

# ─── 清旧产物 ───
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
if (Test-Path $ZipFile) { Remove-Item -Force $ZipFile }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null

# ─── 1. 复制源码 ─────────────────────────────────────
Write-Host "[1/4] 复制 Python 源码..." -ForegroundColor Yellow
$pyFiles = @(
    "app.py", "activity_log.py", "agent_bootstrap.py", "agent_status.py",
    "auth.py", "auto_ingest.py", "config_store.py", "file_parser.py",
    "file_watcher.py", "graph.py", "heartbeat.py", "ingest_batches.py",
    "ingest_service.py", "llm_client.py", "llm_tester.py", "mjq_logging.py",
    "note_intake.py", "orphan_detector.py", "scheduler.py", "schema_runtime.py",
    "user_data.py", "wiki_links.py", "requirements.txt"
)
foreach ($f in $pyFiles) {
    if (Test-Path (Join-Path $RootDir $f)) {
        Copy-Item (Join-Path $RootDir $f) (Join-Path $OutDir $f)
    }
}

# cloud/（仅 jwt_utils 与 __init__）
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "cloud") | Out-Null
foreach ($f in @("__init__.py", "jwt_utils.py")) {
    Copy-Item (Join-Path $RootDir "cloud\$f") (Join-Path $OutDir "cloud\$f")
}

# scripts/
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "scripts") | Out-Null
foreach ($f in @("__init__.py", "bind_user.py")) {
    Copy-Item (Join-Path $RootDir "scripts\$f") (Join-Path $OutDir "scripts\$f")
}

# templates/ + wiki/templates/
if (Test-Path (Join-Path $RootDir "templates")) {
    Copy-Item -Recurse (Join-Path $RootDir "templates") (Join-Path $OutDir "templates")
}
if (Test-Path (Join-Path $RootDir "wiki\templates")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "wiki\templates") | Out-Null
    Copy-Item -Recurse (Join-Path $RootDir "wiki\templates\*") (Join-Path $OutDir "wiki\templates\")
}

# installer/* 到根
foreach ($f in @("setup.bat", "setup.ps1", "start.bat", "start.ps1", "stop.bat", "stop.ps1", "README.txt")) {
    Copy-Item (Join-Path $PSScriptRoot $f) (Join-Path $OutDir $f)
}

# 可选文档
foreach ($f in @("schema.md", "purpose.md")) {
    if (Test-Path (Join-Path $RootDir $f)) {
        Copy-Item (Join-Path $RootDir $f) (Join-Path $OutDir $f)
    }
}

# 预置服务器配置（admin 打包时给）—— 用户解压后 setup.bat 自动读，免填两项
if ($PresetCloudUrl -and $PresetJwt) {
    $PresetPath = Join-Path $OutDir "preset.ini"
    @(
        "# 服务器预置 —— 打包时由 admin 注入，setup.bat 自动读为默认值",
        "MJQ_CLOUD_URL=$PresetCloudUrl",
        "MJQ_JWT_SECRET=$PresetJwt",
        "MJQ_LOCAL_CORS_ORIGINS=$PresetCloudUrl,http://localhost:5174"
    ) | Set-Content -Path $PresetPath -Encoding utf8
    Write-Host "  ✓ preset.ini 已注入（云端 $PresetCloudUrl）" -ForegroundColor Green
}

# ─── 2. 内嵌 Python（bundled 模式） ──────────────────
if (-not $Lite) {
    Write-Host "[2/4] 准备内嵌 Python $EmbedVersion..." -ForegroundColor Yellow

    $EmbedZipPath = Join-Path $CacheDir "python-$EmbedVersion-embed-amd64.zip"
    $GetPipPath = Join-Path $CacheDir "get-pip.py"

    if (-not (Test-Path $EmbedZipPath)) {
        Write-Host "  下载 Python embed ($EmbedVersion, ~10 MB)..." -ForegroundColor White
        try {
            Invoke-WebRequest -Uri $EmbedUrl -OutFile $EmbedZipPath -UseBasicParsing
        } catch {
            Write-Host "  ✗ 下载 Python embed 失败：$_" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "  ✓ 使用缓存的 Python embed" -ForegroundColor Green
    }

    if (-not (Test-Path $GetPipPath)) {
        Write-Host "  下载 get-pip.py..." -ForegroundColor White
        Invoke-WebRequest -Uri $GetPipUrl -OutFile $GetPipPath -UseBasicParsing
    } else {
        Write-Host "  ✓ 使用缓存的 get-pip.py" -ForegroundColor Green
    }

    $EmbedDir = Join-Path $OutDir "python_embed"
    Write-Host "  解压 embed 到 $EmbedDir" -ForegroundColor White
    Expand-Archive -Path $EmbedZipPath -DestinationPath $EmbedDir -Force

    # 改 ._pth：取消 #import site 注释，让 site-packages 生效（pip 才能 import）
    $pthFile = Get-ChildItem -Path $EmbedDir -Filter "python*._pth" | Select-Object -First 1
    if ($pthFile) {
        $content = Get-Content $pthFile.FullName -Raw
        # 处理 "#import site" 和 "# import site" 两种格式
        $content = $content -replace '(?m)^#\s*import\s+site\s*$', 'import site'
        Set-Content -Path $pthFile.FullName -Value $content -Encoding ascii
        Write-Host "  ✓ 修了 ._pth (import site 已启用)" -ForegroundColor Green
    }

    $EmbedPy = Join-Path $EmbedDir "python.exe"

    Write-Host "  装 pip 到 embed Python..." -ForegroundColor White
    & $EmbedPy $GetPipPath --no-warn-script-location 2>&1 | Select-Object -Last 2
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ get-pip 失败" -ForegroundColor Red
        exit 1
    }

    Write-Host "  装项目 requirements（~50-100 MB，慢；首次约 2-4 分钟）..." -ForegroundColor White
    & $EmbedPy -m pip install -r requirements.txt --no-warn-script-location 2>&1 | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ pip install 失败" -ForegroundColor Red
        exit 1
    }

    # 清掉 __pycache__ 缩小尺寸
    Write-Host "  清理 __pycache__..." -ForegroundColor White
    Get-ChildItem -Path $EmbedDir -Filter "__pycache__" -Recurse -Directory |
        ForEach-Object { Remove-Item -Recurse -Force $_.FullName }
    # 清掉 pip wheel cache
    $pipCache = Join-Path $EmbedDir "Lib\site-packages\pip\_vendor"
    if (Test-Path (Join-Path $pipCache "cachecontrol\caches")) {
        Remove-Item -Recurse -Force (Join-Path $pipCache "cachecontrol\caches") -ErrorAction SilentlyContinue
    }

    # 在 OutDir 留个标记，setup/start.ps1 检测有没有内嵌
    "BUNDLED_PYTHON_VERSION=$EmbedVersion" | Out-File (Join-Path $OutDir ".bundled_python") -Encoding ascii

    $embedSize = [math]::Round((Get-ChildItem $EmbedDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    Write-Host "  ✓ 内嵌 Python 完成（$embedSize MB）" -ForegroundColor Green
} else {
    Write-Host "[2/4] -Lite 模式，跳过内嵌 Python" -ForegroundColor Yellow
}

# ─── 3. 打 zip ──────────────────────────────────────
Write-Host "[3/4] 打 zip（大文件，耐心等）..." -ForegroundColor Yellow
Compress-Archive -Path "$OutDir\*" -DestinationPath $ZipFile -CompressionLevel Optimal

$zipSizeMB = [math]::Round((Get-Item $ZipFile).Length / 1MB, 1)
$zipSizeKB = [math]::Round((Get-Item $ZipFile).Length / 1KB, 1)
$sizeLabel = if ($zipSizeMB -ge 1) { "$zipSizeMB MB" } else { "$zipSizeKB KB" }

# ─── 4. 完成 ────────────────────────────────────────
Write-Host "[4/4] 完成" -ForegroundColor Yellow
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  打包完成 ✓  ($Mode)" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  解压目录： $OutDir"
Write-Host "  Zip 文件： $ZipFile ($sizeLabel)"
Write-Host ""
if (-not $Lite) {
    Write-Host "  用户无需自带 Python；解压后双击 setup.bat 即可" -ForegroundColor White
} else {
    Write-Host "  Lite 模式：用户需要自备 Python ≥ 3.10" -ForegroundColor White
}
Write-Host ""
