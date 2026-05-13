param(
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ReleaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ReleaseDir
$FrontendDir = Join-Path $RootDir "frontend"

function Write-Step($message) {
  Write-Host "[desktop-install] $message" -ForegroundColor Cyan
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

if ($DryRun) {
  Write-Step "Would resolve Python 3.10+ and npm."
  Write-Step "Would install Python dependencies from requirements.txt."
  Write-Step "Would install frontend dependencies and build frontend/dist."
  Write-Step "Would create data, wiki, raw, and .env if missing."
  Write-Step "Dry run complete. No files changed and no dependencies installed."
  exit 0
}

$PythonExe = Resolve-Python
$NpmExe = Require-Command "npm.cmd" "Install Node.js 18+ and add npm to PATH."

Write-Step "Python: $PythonExe"
Write-Step "npm: $NpmExe"

Write-Step "Installing Python dependencies"
Push-Location $RootDir
& $PythonExe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
  Pop-Location
  throw "Python dependency installation failed."
}
Pop-Location

Write-Step "Installing frontend dependencies"
Push-Location $FrontendDir
& $NpmExe install
if ($LASTEXITCODE -ne 0) {
  Pop-Location
  throw "Frontend dependency installation failed."
}

Write-Step "Building frontend"
& $NpmExe run build
if ($LASTEXITCODE -ne 0) {
  Pop-Location
  throw "Frontend build failed."
}
Pop-Location

foreach ($dirName in @("data", "wiki", "raw")) {
  $path = Join-Path $RootDir $dirName
  if (-not (Test-Path $path)) {
    New-Item -ItemType Directory -Path $path | Out-Null
    Write-Step "Created $dirName"
  }
}

$EnvPath = Join-Path $RootDir ".env"
$EnvExamplePath = Join-Path $RootDir ".env.example"
if ((-not (Test-Path $EnvPath)) -and (Test-Path $EnvExamplePath)) {
  Copy-Item -Path $EnvExamplePath -Destination $EnvPath
  Write-Step "Created .env from .env.example. Fill LLM settings before production use."
}

Write-Step "Install complete. Run desktop-release\start-desktop.bat to start."
