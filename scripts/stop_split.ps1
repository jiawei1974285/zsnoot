# 停止云本机分离模式三个进程：5004 / 5005 / 5174
$ErrorActionPreference = "Continue"

function Stop-PortListener($port, $label) {
    $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $listeners) {
        Write-Host "[ ] Port $port ($label): no listener" -ForegroundColor Gray
        return
    }
    $procIds = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $procIds) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "[*] Killing $label (PID=$procId, $($proc.ProcessName))..." -ForegroundColor Yellow
            Stop-Process -Id $procId -Force
        }
    }
}

Write-Host "=== mjq cloud-split stop ===" -ForegroundColor Cyan
Stop-PortListener 5004 "agent"
Stop-PortListener 5005 "cloud"
Stop-PortListener 5174 "frontend"
Start-Sleep -Milliseconds 500

$still = (Get-NetTCPConnection -LocalPort 5004 -State Listen -ErrorAction SilentlyContinue) +
         (Get-NetTCPConnection -LocalPort 5005 -State Listen -ErrorAction SilentlyContinue) +
         (Get-NetTCPConnection -LocalPort 5174 -State Listen -ErrorAction SilentlyContinue)
if ($still) {
    Write-Host "[!] Some listeners still up; please check." -ForegroundColor Red
} else {
    Write-Host "[+] All stopped." -ForegroundColor Green
}
