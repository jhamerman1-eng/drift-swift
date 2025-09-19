@echo off
echo Setting up environment for devnet Swift MM bot...

REM Set correct environment variables for devnet
set DRIFT_ENV=devnet
set SWIFT_FORWARD_BASE=https://beta.drift.trade
set SWIFT_WS_URL=wss://beta.drift.trade/ws

echo Environment configured:
echo DRIFT_ENV=%DRIFT_ENV%
echo SWIFT_FORWARD_BASE=%SWIFT_FORWARD_BASE%
echo SWIFT_WS_URL=%SWIFT_WS_URL%

echo.
echo Starting Swift MM bot with correct configuration...
python run_swift_mm_complete.py

pause
