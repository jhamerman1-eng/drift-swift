# ==============================================================================
# 🚨 QUICK SHUTDOWN SCRIPT - OFF COMMAND
# ==============================================================================
# Usage: ./OFF.ps1 or .\OFF.ps1
# This script gracefully stops all bots and services for fresh testing
# ==============================================================================

Write-Host "🔴 SHUTTING DOWN ALL BOTS AND SERVICES..." -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red

# Get initial process counts
$initialPython = (Get-Process -Name "python*" -ErrorAction SilentlyContinue | Measure-Object).Count
$initialAll = (Get-Process | Measure-Object).Count

Write-Host "📊 Initial Status:" -ForegroundColor Yellow
Write-Host "   - Python processes: $initialPython" -ForegroundColor Yellow
Write-Host "   - Total processes: $initialAll" -ForegroundColor Yellow

# 1. Stop all Python processes (bots)
Write-Host "`n🤖 Stopping Python Bot Processes..." -ForegroundColor Cyan
$pythonProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | ForEach-Object {
        Write-Host "   - Stopping: $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "✅ All Python processes stopped" -ForegroundColor Green
} else {
    Write-Host "   - No Python processes found" -ForegroundColor Gray
}

# 2. Stop Swift sidecar service (port 8787)
Write-Host "`n🌐 Stopping Swift Sidecar Service..." -ForegroundColor Cyan
$sidecarProcess = netstat -ano | findstr ":8787" | findstr "LISTENING"
if ($sidecarProcess) {
    $processId = ($sidecarProcess -split '\s+')[-1]
    Write-Host "   - Stopping sidecar service (PID: $processId)" -ForegroundColor Gray
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    Write-Host "✅ Swift sidecar stopped" -ForegroundColor Green
} else {
    Write-Host "   - No Swift sidecar service found on port 8787" -ForegroundColor Gray
}

# 3. Verify shutdown
Start-Sleep -Milliseconds 500
$finalPython = (Get-Process -Name "python*" -ErrorAction SilentlyContinue | Measure-Object).Count
$finalPort8787 = netstat -ano | findstr ":8787" | findstr "LISTENING"

Write-Host "`n📊 Final Status:" -ForegroundColor Yellow
Write-Host "   - Python processes: $finalPython" -ForegroundColor Yellow
if ($finalPort8787) {
    Write-Host "   - Port 8787: STILL ACTIVE ⚠️" -ForegroundColor Red
} else {
    Write-Host "   - Port 8787: FREE ✅" -ForegroundColor Green
}

# 4. Summary
$stoppedPython = $initialPython - $finalPython
Write-Host "`n🎯 SHUTDOWN SUMMARY:" -ForegroundColor Magenta
Write-Host "   - Python processes stopped: $stoppedPython" -ForegroundColor Magenta
if ($sidecarProcess -and -not $finalPort8787) {
    Write-Host "   - Swift sidecar: STOPPED ✅" -ForegroundColor Green
} elseif ($sidecarProcess) {
    Write-Host "   - Swift sidecar: STILL RUNNING ⚠️" -ForegroundColor Red
} else {
    Write-Host "   - Swift sidecar: NOT FOUND (already stopped)" -ForegroundColor Gray
}

Write-Host "`n🏁 READY FOR FRESH TEST!" -ForegroundColor Green
Write-Host "   Use: python launch_bot_universal.py --bot <bot_name> --env <environment>" -ForegroundColor Cyan
Write-Host "   Example: python launch_bot_universal.py --bot hedge --env devnet" -ForegroundColor Cyan
