@echo off
REM 🚀 Quick Start Script for Drift Bots v3.0 - Beta.Drift.Trade (Windows)
REM Usage: start_beta_bots.bat [--dry-run] [--mock] [--real]

setlocal enabledelayedexpansion

echo 🚀 Drift Bots v3.0 - Beta.Drift.Trade Launcher
echo ==================================================

REM Default settings
set DRY_RUN=false
set USE_MOCK=true
set CONFIG_FILE=beta_environment_config.yaml

REM Parse arguments
:parse_args
if "%~1"=="" goto :end_parse
if "%~1"=="--dry-run" (
    set DRY_RUN=true
    shift
    goto :parse_args
)
if "%~1"=="--real" (
    set USE_MOCK=false
    shift
    goto :parse_args
)
if "%~1"=="--mock" (
    set USE_MOCK=true
    shift
    goto :parse_args
)
if "%~1"=="--config" (
    set CONFIG_FILE=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--help" (
    echo 🚀 Drift Bots v3.0 - Beta.Drift.Trade Quick Start
    echo.
    echo Usage:
    echo   start_beta_bots.bat              # Launch in mock mode (safe)
    echo   start_beta_bots.bat --real       # Launch in live mode (uses real wallet!)
    echo   start_beta_bots.bat --dry-run    # Preview configuration without launching
    echo   start_beta_bots.bat --config FILE # Use custom configuration file
    echo.
    echo Examples:
    echo   start_beta_bots.bat --dry-run    # Safe preview
    echo   start_beta_bots.bat --mock       # Test with mock client
    echo   start_beta_bots.bat --real       # LIVE TRADING - USE WITH CAUTION!
    goto :eof
)
echo ❌ Unknown option: %~1
echo Use --help for usage information
goto :eof

:end_parse

REM Check if configuration exists
if not exist "%CONFIG_FILE%" (
    echo ❌ Configuration file not found: %CONFIG_FILE%
    echo 💡 Create it by copying and modifying beta_environment_config.yaml
    goto :eof
)

REM Check if wallet exists (simple check)
findstr /C:"maker_keypair_path:" "%CONFIG_FILE%" >nul 2>&1
if errorlevel 1 (
    echo ❌ Could not find wallet path in configuration
    goto :eof
)

echo ✅ Configuration file found: %CONFIG_FILE%
echo 🔧 Mode: %USE_MOCK%
if "%USE_MOCK%"=="true" (
    echo 🔧 Trading Mode: MOCK (safe - no real trades)
) else (
    echo 🔥 Trading Mode: LIVE (real trades will be placed!)
    echo ⚠️  Ensure your wallet has sufficient SOL for fees
)

if "%DRY_RUN%"=="true" (
    echo 🔍 DRY RUN MODE - Configuration preview only
    python launch_beta_bots.py --dry-run --config "%CONFIG_FILE%"
    goto :eof
)

REM Safety confirmation for live trading
if "%USE_MOCK%"=="false" (
    echo.
    echo 🔥 LIVE TRADING MODE DETECTED!
    echo ⚠️  This will place REAL trades on beta.drift.trade
    echo ⚠️  Ensure your wallet has sufficient SOL for fees
    echo ⚠️  Risk management settings will be active
    echo.
    set /p confirm="Are you sure you want to proceed with LIVE trading? (yes/no): "
    if /i not "!confirm!"=="yes" (
        echo ✅ Launch cancelled. Use --mock for safe testing.
        goto :eof
    )
)

echo.
echo 🚀 Launching Drift Bots v3.0...

REM Launch the bots
python launch_beta_bots.py --config "%CONFIG_FILE%"

echo ✅ Launch process completed!
pause
