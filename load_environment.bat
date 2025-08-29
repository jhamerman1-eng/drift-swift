@echo off
REM Load Environment Variables from .env file
REM This script loads your saved environment configuration

echo.
echo 🔄 Loading Environment Configuration
echo =====================================

REM Check if .env file exists
if not exist ".env" (
    echo ❌ ERROR: .env file not found!
    echo.
    echo 💡 Please run setup_environment.bat first to create your environment file
    echo.
    pause
    exit /b 1
)

echo 📁 Loading environment variables from .env file...

REM Load environment variables from .env file
for /f "tokens=*" %%i in (.env) do (
    REM Skip comments and empty lines
    echo %%i | findstr /r "^#" >nul
    if errorlevel 1 (
        echo %%i | findstr "=" >nul
        if not errorlevel 1 (
            REM Extract key and value
            for /f "tokens=1,* delims==" %%a in ("%%i") do (
                set "%%a=%%b"
                echo   ✅ Set %%a
            )
        )
    )
)

echo.
echo ✅ Environment variables loaded successfully!
echo.
echo 🔑 Current configuration:
echo   DRIFT_API_KEY: [HIDDEN FOR SECURITY]
echo   DRIFT_CLUSTER: %DRIFT_CLUSTER%
echo   DRIFT_KEYPAIR_PATH: %DRIFT_KEYPAIR_PATH%
echo   USE_MOCK: %USE_MOCK%
echo   SWIFT_BASE: %SWIFT_BASE%
echo.
echo 🎯 You can now run setup_devnet_trading.bat
echo.

pause


