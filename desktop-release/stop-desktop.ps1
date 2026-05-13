param(
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ReleaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = Join-Path $ReleaseDir "runtime"
$PidPath = Join-Path $RuntimeDir "backend.pid"

function Write-Step($message) {
  Write-Host "[desktop-stop] $message" -ForegroundColor Cyan
}

if ($DryRun) {
  Write-Step "Dry run complete. No process was stopped."
  exit 0
}

$stopped = $false

if (Test-Path $PidPath) {
  $pidText = Get-Content -Path $PidPath -ErrorAction SilentlyContinue | Select-Object -First 1
  $procId = 0
  if ([int]::TryParse($pidText, [ref]$procId)) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Step "Stopping backend PID $procId"
      Stop-Process -Id $procId -Force
      $stopped = $true
    }
  }
  Remove-Item -Path $PidPath -Force -ErrorAction SilentlyContinue
}

if (-not $stopped) {
  $listener = Get-NetTCPConnection -LocalPort 5004 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($listener) {
    $procId = $listener.OwningProcess
    Write-Step "Stopping process on port 5004, PID $procId"
    Stop-Process -Id $procId -Force
    $stopped = $true
  }
}

if ($stopped) {
  Write-Step "Stopped."
} else {
  Write-Step "No running backend found."
}

