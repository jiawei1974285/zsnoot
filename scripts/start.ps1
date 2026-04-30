# One-click start: backend (Flask, 5004) + frontend (Vite dev, 5174)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\start.ps1
#   or double-click scripts\start.bat
#
# Two new terminal windows will pop up; close them to stop.
# Note: All output here is ASCII to stay safe on Windows PowerShell 5.1
# (which reads .ps1 files in the system codepage, not UTF-8).

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $RootDir "frontend"

function Resolve-Python {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }

  $bundled = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
  if (Test-Path $bundled) { return $bundled }

  throw "Python was not found. Install Python or add it to PATH."
}

$PythonExe = Resolve-Python

Write-Host "=== mjq-handynotes one-click start ===" -ForegroundColor Cyan
Write-Host "Project root: $RootDir"
Write-Host ""

# ---- 1. Port-occupancy check ------------------------------------------
function Test-Port($port, $label) {
  $existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if ($existing) {
    # Note: $pid is a PowerShell automatic read-only variable, so use $procId.
    $procId = $existing[0].OwningProcess
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    Write-Host "[!] Port $port ($label) is in use: PID=$procId Name=$($proc.ProcessName)" -ForegroundColor Yellow
    $reply = Read-Host "    Kill that process and continue? [y/N]"
    if ($reply -eq 'y' -or $reply -eq 'Y') {
      Stop-Process -Id $procId -Force
      Start-Sleep -Milliseconds 500
      Write-Host "    Killed PID $procId" -ForegroundColor Green
    } else {
      Write-Host "    Aborting. Free the port and retry." -ForegroundColor Red
      exit 1
    }
  }
}

Test-Port 5004 "backend Flask"
Test-Port 5174 "frontend Vite"

# ---- 2. Dependency check ----------------------------------------------
$NodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $NodeModules)) {
  Write-Host "[!] frontend/node_modules missing, running npm install..." -ForegroundColor Yellow
  Push-Location $FrontendDir
  npm install
  if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "    npm install failed, abort." -ForegroundColor Red
    exit 1
  }
  Pop-Location
  Write-Host "    Frontend deps installed." -ForegroundColor Green
}

# Python deps: only check importability (avoid pip-installing every run).
$pythonOk = $false
try {
  & $PythonExe -c "import flask, yaml, requests" 2>$null
  if ($LASTEXITCODE -eq 0) { $pythonOk = $true }
} catch { }
if (-not $pythonOk) {
  Write-Host "[!] Python deps incomplete, running pip install -r requirements.txt..." -ForegroundColor Yellow
  Push-Location $RootDir
  & $PythonExe -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "    pip install failed, abort." -ForegroundColor Red
    exit 1
  }
  Pop-Location
  Write-Host "    Python deps installed." -ForegroundColor Green
}

# ---- 3. Launch backend (new window) -----------------------------------
Write-Host ""
Write-Host "[*] Starting backend Flask (port 5004)..." -ForegroundColor Cyan
$backendCmd = "& { Set-Location '$RootDir'; `$Host.UI.RawUI.WindowTitle='mjq-backend (5004)'; & '$PythonExe' app.py }"
Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $backendCmd | Out-Null

# ---- 4. Launch frontend dev (new window) ------------------------------
Write-Host "[*] Starting frontend Vite (port 5174)..." -ForegroundColor Cyan
$frontendCmd = "& { Set-Location '$FrontendDir'; `$Host.UI.RawUI.WindowTitle='mjq-frontend (5174)'; npm.cmd run dev }"
Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $frontendCmd | Out-Null

# ---- 5. Wait for backend ----------------------------------------------
Write-Host ""
Write-Host "[*] Waiting for backend to be ready..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Seconds 1
  try {
    $resp = Invoke-WebRequest -Uri "http://localhost:5004/api/auth/status" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
    if ($resp.StatusCode -eq 200) { $ready = $true; break }
  } catch { }
}
if ($ready) {
  Write-Host "    Backend is up." -ForegroundColor Green
} else {
  Write-Host "    Backend not ready in 20s; check the backend window for errors." -ForegroundColor Yellow
}

# ---- 6. Print URLs ----------------------------------------------------
Write-Host ""
Write-Host "=== Started ===" -ForegroundColor Green
Write-Host "  Backend API: http://localhost:5004" -ForegroundColor White
Write-Host "  Frontend:    http://localhost:5174  (recommended, hot-reload)" -ForegroundColor White
Write-Host "  Logs:        $RootDir\mjq.log"
Write-Host ""
Write-Host "Stop: close both popup terminals, or run scripts\stop.ps1"
