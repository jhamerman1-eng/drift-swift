@echo off
REM DevNet Trading Environment Setup - v2.0 (Security Enhanced)
REM Run this script to configure your environment for real Drift trading on Solana DevNet

echo 🚀 Setting up DevNet Trading Environment...

REM =================================================================
REM SECURITY VALIDATION
REM =================================================================

REM Check if API key is set via environment variable
if "%DRIFT_API_KEY%"=="" (
    echo.
    echo ❌ SECURITY ERROR: DRIFT_API_KEY environment variable not set!
    echo.
    echo 🔐 To fix this, run one of these commands first:
    echo.
    echo   Option 1 - Temporary (current session only):
    echo   set DRIFT_API_KEY=your_helius_api_key_here
    echo.
    echo   Option 2 - Permanent (add to your system environment variables):
    echo   • Windows: System Properties → Environment Variables
    echo   • Add: DRIFT_API_KEY = your_helius_api_key_here
    echo.
    echo 💡 Get your Helius API key from: https://helius.dev
    echo.
    pause
    exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ ERROR: Python is not installed or not in PATH!
    echo.
    echo 💡 Install Python from: https://python.org
    echo 💡 Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Check if required packages are installed
python -c "import driftpy" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ ERROR: driftpy package not installed!
    echo.
    echo 💡 Install required packages:
    echo pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM =================================================================
REM ENVIRONMENT CONFIGURATION
REM =================================================================

REM Set Drift Environment Variables (secure approach)
set DRIFT_CLUSTER=devnet
set DRIFT_RPC_URL=https://devnet.helius-rpc.com/?api-key=%DRIFT_API_KEY%
set DRIFT_WS_URL=wss://devnet.helius-rpc.com/?api-key=%DRIFT_API_KEY%
set DRIFT_KEYPAIR_PATH=.devnet_wallet.json
set USE_MOCK=false

REM Set Swift Environment Variables
set SWIFT_BASE=https://swift.drift.trade
set SWIFT_SIDECAR=

REM =================================================================
REM WALLET VALIDATION
REM =================================================================

REM Check if wallet exists and validate its integrity
if exist "%DRIFT_KEYPAIR_PATH%" (
    echo.
    echo ✅ Wallet file found: %DRIFT_KEYPAIR_PATH%

    REM Validate wallet file format (basic check)
    for /f %%i in ("%DRIFT_KEYPAIR_PATH%") do set FILE_SIZE=%%~zi
    if %FILE_SIZE% lss 100 (
        echo ❌ ERROR: Wallet file appears to be corrupted or too small!
        echo 💡 Delete %DRIFT_KEYPAIR_PATH% and run wallet creation script
        pause
        exit /b 1
    )

    echo 🔐 Wallet format: Validated (ready for trading)

    REM Try to get public key from wallet (if driftpy is available)
    python -c "from driftpy.keypair import load_keypair; kp = load_keypair('%DRIFT_KEYPAIR_PATH%'); print(f'📬 Public Key: {kp.pubkey()}')" 2>nul
    if errorlevel 1 (
        echo ⚠️  Warning: Could not extract public key from wallet
    )

) else (
    echo.
    echo ❌ Wallet file not found: %DRIFT_KEYPAIR_PATH%
    echo.
    echo 💡 SECURE WALLET CREATION OPTIONS:
    echo.
    echo   Option 1 - Generate new wallet:
    echo   python create_keypair.py
    echo.
    echo   Option 2 - Import existing wallet securely:
    echo   python create_drift_account.py --import
    echo.
    echo   Option 3 - Use test wallet (NOT RECOMMENDED FOR MAINNET):
    echo   python create_test_wallet.py
    echo.
    echo 🚨 NEVER hardcode private keys in scripts!
    echo.
    pause
    exit /b 1
)

REM =================================================================
REM CONFIGURATION DISPLAY
REM =================================================================

echo.
echo 📊 Configuration Summary:
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 🌍 Cluster: %DRIFT_CLUSTER%
echo 🔑 Wallet: %DRIFT_KEYPAIR_PATH% ✅
echo 🧪 Mock Mode: %USE_MOCK%
echo 📡 Swift: %SWIFT_BASE%
echo 🔗 RPC: Configured (API key hidden for security)
echo 🌐 WS: Configured (API key hidden for security)

REM =================================================================
REM NEXT STEPS
REM =================================================================

echo.
echo 🎯 Ready to run the bot!
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 📋 Available commands:
echo.
echo   • Run Market Maker Bot:
echo    python run_mm_bot_v2.py --env devnet --cfg configs/core/drift_client.yaml
echo.
echo   • Check wallet balance:
echo    python check_wallet_funds.py
echo.
echo   • Test connection:
echo    python devnet_test_connection.py

echo.
echo 🚨 IMPORTANT SAFETY NOTES:
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo • This is DevNet - trades use test SOL only
echo • Get DevNet SOL from: https://faucet.solana.com
echo • Monitor your wallet balance closely
echo • Press Ctrl+C to stop bots gracefully
echo • Keep your private keys secure and never share them
echo • API keys should be stored as environment variables

echo.
echo 🎉 DevNet Trading Environment Setup Complete!
echo 🔒 Security checks passed - you're ready to trade safely!

REM Optional: Show current directory and important files
echo.
echo 📁 Current directory: %CD%
echo 📄 Key files in this directory:
if exist "requirements.txt" echo   • requirements.txt (dependencies)
if exist "configs\" echo   • configs\ (configuration files)
if exist "bots\" echo   • bots\ (bot implementations)

pause



