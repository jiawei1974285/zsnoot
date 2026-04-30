# One-click stop: kill processes listening on 5004 (backend) and 5174 (frontend)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
#
# Only kills the listeners on those two ports - won't touch other python/node.
# All output is ASCII to stay safe on Windows PowerShell 5.1.

$ErrorActionPreference = "Continue"

function Stop-PortListener($port, $label) {
  $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if (-not $listeners) {
    Write-Host "[ ] Port $port ($label): no listener" -ForegroundColor Gray
    return
  }
  # Note: $pid is a PowerShell automatic read-only variable, so use $procId.
  $procIds = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procId in $procIds) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "[*] Killing $label (PID=$procId, $($proc.ProcessName))..." -ForegroundColor Yellow
      Stop-Process -Id $procId -Force
    }
  }
}

Write-Host "=== mjq-handynotes one-click stop ===" -ForegroundColor Cyan
Stop-PortListener 5004 "backend Flask"
Stop-PortListener 5174 "frontend Vite"
Start-Sleep -Milliseconds 500

# Re-check
$still = (Get-NetTCPConnection -LocalPort 5004 -State Listen -ErrorAction SilentlyContinue) +
         (Get-NetTCPConnection -LocalPort 5174 -State Listen -ErrorAction SilentlyContinue)
if ($still) {
  Write-Host "[!] Some listeners are still up; please check." -ForegroundColor Red
} else {
  Write-Host "[+] All stopped." -ForegroundColor Green
}
