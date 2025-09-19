Param(
    [string]$ExpectedVersion = "1.17.0-rc3",
    [string]$MetricsPort = "8000"
)

$ErrorActionPreference = "Stop"
$global:FAILED = $false

function Pass([string]$msg) { Write-Host "[PASS] $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail([string]$msg) { 
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    $global:FAILED = $true
}

Write-Host "=== Drift v1.17 (rc3) Preflight ===" -ForegroundColor Cyan

# 1) Solana CLI
try {
    $sol = Get-Command solana -ErrorAction Stop
    Pass "Solana CLI found at $($sol.Source)"
    $ver = & solana --version
    Pass "Solana version: $ver"
} catch {
    Fail "Solana CLI not found in PATH."
}

# 2) Solana config and wallet
try {
    $cfg = & solana config get | Out-String
    Write-Host $cfg
    # Parse key fields
    $rpc = ($cfg -split "`n" | Where-Object {$_ -match "RPC URL"}).Split(":")[1].Trim()
    $kpLine = ($cfg -split "`n" | Where-Object {$_ -match "Keypair Path"})
    $kp = $kpLine.Substring($kpLine.IndexOf(":")+1).Trim()
    if (Test-Path $kp) { Pass "Keypair exists: $kp" } else { Fail "Keypair file missing: $kp" }
    $addr = & solana address
    Pass "Default address: $addr"
    try { 
        $bal = & solana balance
        Pass "Balance: $bal"
    } catch { Warn "Could not fetch balance (RPC or cluster issue?)" }
    try {
        $slot = & solana slot
        if ($slot -match '^\d+$') { Pass "RPC reachable, current slot: $slot" } else { Warn "Unexpected slot output: $slot" }
    } catch {
        Fail "RPC slot check failed for $rpc"
    }
} catch {
    Fail "Failed to read Solana config: $($_.Exception.Message)"
}

# 3) Environment variables for bot
$kpEnv = $env:KEYPAIR_PATH
if ($kpEnv) {
    if ($kpEnv -ne $kp) {
        Warn "KEYPAIR_PATH env ($kpEnv) != Solana keypair path ($kp). Bots may use env var; consider aligning."
    } else {
        Pass "KEYPAIR_PATH env matches Solana keypair."
    }
} else {
    Warn "KEYPAIR_PATH env not set. Bots may default to Solana path."
}

if ($env:JITO_KEYPAIR_PATH) {
    if (Test-Path $env:JITO_KEYPAIR_PATH) { Pass "JITO_KEYPAIR_PATH set and file exists." }
    else { Warn "JITO_KEYPAIR_PATH set but file not found: $env:JITO_KEYPAIR_PATH" }
} else {
    Warn "JITO_KEYPAIR_PATH not set (only needed if using Jito)."
}

if ($env:DRIFT_CLUSTER) { Pass "DRIFT_CLUSTER=$($env:DRIFT_CLUSTER)" } else { Warn "DRIFT_CLUSTER not set (devnet/testnet/mainnet)." }
if ($env:DRIFT_HTTP_URL) { Pass "DRIFT_HTTP_URL=$($env:DRIFT_HTTP_URL)" } else { Warn "DRIFT_HTTP_URL not set (RPC endpoint)." }
if ($env:DRIFT_WS_URL) { Pass "DRIFT_WS_URL=$($env:DRIFT_WS_URL)" } else { Warn "DRIFT_WS_URL not set (WS endpoint)." }

# 4) Swift (sidecar or direct)
$swiftBase = $env:SWIFT_FORWARD_BASE
if ($swiftBase) {
    $health = "$swiftBase".TrimEnd("/") + "/health"
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Uri $health
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
            Pass "Swift forwarder healthy: $health ($($resp.StatusCode))"
        } else {
            Warn "Swift forwarder responded with $($resp.StatusCode): $health"
        }
    } catch {
        Fail "Swift forwarder not reachable at $health"
    }
} else {
    Warn "SWIFT_FORWARD_BASE not set. If using direct Swift API, ensure your driver config points to it."
}

# 5) Bot metrics port (Prometheus) check
try {
    $tnc = Test-NetConnection -ComputerName localhost -Port ([int]$MetricsPort) -WarningAction SilentlyContinue
    if ($tnc.TcpTestSucceeded) { Pass "Metrics port reachable on localhost:$MetricsPort" }
    else { Warn "Metrics port not reachable on localhost:$MetricsPort (bot not running or different port)" }
} catch {
    Warn "Could not test metrics port $MetricsPort"
}

# 6) VERSION file sanity (repo root)
try {
    $here = Get-Location
    $verPath = Join-Path $here "VERSION"
    if (Test-Path $verPath) {
        $content = (Get-Content $verPath | Select-Object -First 1).Trim()
        if ($content -eq $ExpectedVersion) {
            Pass "VERSION file matches expected: $content"
        } else {
            Warn "VERSION file found ($content) but expected $ExpectedVersion"
        }
    } else {
        Warn "VERSION file not found (optional)."
    }
} catch {
    Warn "VERSION check failed."
}

if ($global:FAILED) {
    Write-Host "`nOne or more critical checks FAILED." -ForegroundColor Red
    exit 1
} else {
    Write-Host "`nAll critical checks passed ✅" -ForegroundColor Green
    exit 0
}
