@echo off
REM ==============================================================================
REM 🚨 QUICK SHUTDOWN BATCH FILE - OFF COMMAND
REM ==============================================================================
REM Usage: OFF.bat or just OFF
REM This script gracefully stops all bots and services for fresh testing
REM ==============================================================================

echo.
echo 🔴 SHUTTING DOWN ALL BOTS AND SERVICES...
echo ============================================
echo.

REM Run the PowerShell script
powershell.exe -ExecutionPolicy Bypass -File "%~dp0OFF.ps1"

echo.
echo 🏁 SHUTDOWN COMPLETE!
echo.
pause
