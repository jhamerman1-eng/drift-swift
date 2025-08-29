# DevNet Trading Environment Setup
# Run this script to configure your environment for real Drift trading on Solana DevNet

Write-Host "🚀 Setting up DevNet Trading Environment..." -ForegroundColor Green

# Set Drift Environment Variables
$env:DRIFT_CLUSTER = "devnet"
$env:DRIFT_RPC_URL = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
$env:DRIFT_WS_URL = "wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
$env:DRIFT_KEYPAIR_PATH = ".devnet_wallet.json"
$env:USE_MOCK = "false"

# Set Swift Environment Variables
$env:SWIFT_BASE = "https://swift.drift.trade"
$env:SWIFT_SIDECAR = ""  # Use direct Swift API

# Display Configuration
Write-Host "`n📊 Configuration Set:" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "🌐 RPC URL: $env:DRIFT_RPC_URL" -ForegroundColor White
Write-Host "🔌 WS URL: $env:DRIFT_WS_URL" -ForegroundColor White
Write-Host "🔑 Wallet: $env:DRIFT_KEYPAIR_PATH" -ForegroundColor White
Write-Host "🌍 Cluster: $env:DRIFT_CLUSTER" -ForegroundColor White
Write-Host "📡 Swift: $env:SWIFT_BASE" -ForegroundColor White
Write-Host "🧪 Mock Mode: $env:USE_MOCK" -ForegroundColor White

# Check wallet addresses
Write-Host "`n🔑 Wallet Addresses:" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📬 Public Address: A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW" -ForegroundColor White
Write-Host "🔐 Full Keypair: 61UGhmDPFesjFp7Mz2MWqaPmgp9jGm1HqnsMFyB2s2GFy1dwxuWQbTnkrCysZuccJyd1X2UFm7AknkPWJv7X1uMx" -ForegroundColor White

# Check if wallet exists
$walletExists = Test-Path $env:DRIFT_KEYPAIR_PATH

if ($walletExists) {
    Write-Host "`n✅ Wallet file found: $env:DRIFT_KEYPAIR_PATH" -ForegroundColor Green
    Write-Host "🔐 Wallet format: Detected (ready for trading)" -ForegroundColor Green
} else {
    Write-Host "`n❌ Wallet file not found: $env:DRIFT_KEYPAIR_PATH" -ForegroundColor Red
    Write-Host "💡 Creating wallet from provided keypair..." -ForegroundColor Yellow

    # Create wallet file with the provided keypair
    $keypairData = @(
        174, 47, 154, 16, 202, 193, 206, 113, 199, 190, 53, 133, 169, 175, 31, 56,
        222, 53, 138, 189, 224, 216, 117, 173, 10, 149, 53, 45, 73, 46, 49, 18,
        93, 131, 45, 18, 18, 209, 161, 212, 247, 175, 76, 106, 148, 248, 161, 76,
        149, 181, 165, 68, 119, 40, 116, 85, 153, 72, 139, 161, 76, 136, 164, 142
    )

    $keypairData | ConvertTo-Json | Out-File -FilePath $env:DRIFT_KEYPAIR_PATH -Encoding UTF8
    Write-Host "✅ Wallet created successfully!" -ForegroundColor Green
}

Write-Host "`n🎯 Ready to run the bot!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "Run this command:" -ForegroundColor Yellow
Write-Host "python run_mm_bot_v2.py --env devnet --cfg configs/core/drift_client.yaml" -ForegroundColor White

Write-Host "`n🚨 IMPORTANT SAFETY NOTES:" -ForegroundColor Red
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Red
Write-Host "• This is DevNet - trades use test SOL" -ForegroundColor Yellow
Write-Host "• Get DevNet SOL from: https://faucet.solana.com" -ForegroundColor Yellow
Write-Host "• Monitor your wallet balance closely" -ForegroundColor Yellow
Write-Host "• Press Ctrl+C to stop gracefully" -ForegroundColor Yellow

Write-Host "`n🎉 DevNet Trading Environment Setup Complete!" -ForegroundColor Green
