# 停止本机 agent（杀 5004 监听进程）
$existing = Get-NetTCPConnection -LocalPort 5004 -State Listen -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "端口 5004 没有进程在监听，无需停止" -ForegroundColor Gray
} else {
    foreach ($conn in $existing) {
        $procId = $conn.OwningProcess
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "杀掉 PID=$procId ($($proc.ProcessName))" -ForegroundColor Yellow
            Stop-Process -Id $procId -Force
        }
    }
    Start-Sleep -Milliseconds 500
    Write-Host "✓ 已停止" -ForegroundColor Green
}
Start-Sleep -Seconds 1
