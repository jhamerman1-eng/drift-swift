# Simple Swift Sidecar Fix
# Fixes the Swift sidecar configuration and restarts it

Write-Host "Starting Swift Sidecar Fix..." -ForegroundColor Green

# Step 1: Stop current sidecar
Write-Host "Step 1: Stopping current sidecar..." -ForegroundColor Yellow
docker-compose -f docker-compose.swift.yml down

# Step 2: Start sidecar with corrected config (already fixed in docker-compose.swift.yml)
Write-Host "Step 2: Starting sidecar with corrected configuration..." -ForegroundColor Yellow
docker-compose -f docker-compose.swift.yml up -d

# Step 3: Wait for startup
Write-Host "Step 3: Waiting for sidecar startup..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Step 4: Check if running
Write-Host "Step 4: Checking if sidecar is running..." -ForegroundColor Yellow
$running = docker ps | findstr swift-mm
if ($running) {
    Write-Host "SUCCESS: Sidecar is running" -ForegroundColor Green
} else {
    Write-Host "ERROR: Sidecar not running" -ForegroundColor Red
}

# Step 5: Test health endpoint
Write-Host "Step 5: Testing health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8787/health" -UseBasicParsing -TimeoutSec 10
    $healthData = $response.Content | ConvertFrom-Json
    $mode = $healthData.mode
    $forward = $healthData.forward
    
    Write-Host "Sidecar Mode: $mode" -ForegroundColor Cyan
    Write-Host "Forward URL: $forward" -ForegroundColor Cyan
    
    if ($mode -eq "forward") {
        Write-Host "SUCCESS: Sidecar is in FORWARD mode!" -ForegroundColor Green
        Write-Host "Swift API integration is now enabled!" -ForegroundColor Green
    } else {
        Write-Host "WARNING: Sidecar is in $mode mode" -ForegroundColor Yellow
    }
} catch {
    Write-Host "ERROR: Health check failed - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nFix completed. Check the results above." -ForegroundColor Magenta
