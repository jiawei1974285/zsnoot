param(
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ReleaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ReleaseDir
$RuntimeDir = Join-Path $ReleaseDir "runtime"
$PidPath = Join-Path $RuntimeDir "backend.pid"
$LogPath = Join-Path $RuntimeDir "backend.out.log"
$ErrPath = Join-Path $RuntimeDir "backend.err.log"
$DistDir = Join-Path $RootDir "frontend\dist"
$AppPath = Join-Path $RootDir "app.py"

function Write-Step($message) {
  Write-Host "[desktop-start] $message" -ForegroundColor Cyan
}

function Require-Command($name, $hint) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $cmd) {
    throw "$name was not found. $hint"
  }
  return $cmd.Source
}

function Resolve-Python {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }

  $bundled = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
  if (Test-Path $bundled) { return $bundled }

  throw "python was not found. Install Python 3.10+ and add it to PATH."
}

Write-Step "Project root: $RootDir"

if (-not (Test-Path $AppPath)) {
  throw "app.py was not found at $AppPath"
}

if ($DryRun) {
  Write-Step "Would verify frontend\dist exists."
  Write-Step "Would resolve Python 3.10+."
  Write-Step "Would start app.py on http://localhost:5004 and write runtime\backend.pid."
  Write-Step "Would open http://localhost:5004 when ready."
  Write-Step "Dry run complete. Backend was not started."
  exit 0
}

if (-not (Test-Path $DistDir)) {
  throw "frontend\dist was not found. Run desktop-release\install.ps1 first."
}

$PythonExe = Resolve-Python

if (-not (Test-Path $RuntimeDir)) {
  New-Item -ItemType Directory -Path $RuntimeDir | Out-Null
}

$existing = Get-NetTCPConnection -LocalPort 5004 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
  Write-Step "Port 5004 is already listening. Opening browser."
  Start-Process "http://localhost:5004"
  exit 0
}

Write-Step "Starting backend on http://localhost:5004"
$process = Start-Process -FilePath $PythonExe `
  -ArgumentList "app.py" `
  -WorkingDirectory $RootDir `
  -WindowStyle Hidden `
  -RedirectStandardOutput $LogPath `
  -RedirectStandardError $ErrPath `
  -PassThru

Set-Content -Path $PidPath -Value $process.Id -Encoding ASCII

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 1
  try {
    $resp = Invoke-WebRequest -Uri "http://localhost:5004/api/auth/status" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
    if ($resp.StatusCode -eq 200) {
      $ready = $true
      break
    }
  } catch { }
}

if (-not $ready) {
  Write-Host "Backend did not become ready in 30 seconds. Check $ErrPath" -ForegroundColor Yellow
  exit 1
}

Write-Step "Backend is ready. Opening browser."
Start-Process "http://localhost:5004"
