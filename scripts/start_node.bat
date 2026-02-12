@echo off
REM Start MiniDOS Node Daemon

echo ========================================
echo   Starting MiniDOS Node Daemon
echo ========================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires Administrator privileges!
    echo Please right-click and select "Run as Administrator"
    pause
    exit /b 1
)

REM Change to project root
cd /d "%~dp0.."

REM Check if Python is available
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please run tools\installer\install_dependencies.ps1 first
    pause
    exit /b 1
)

REM Check if config exists
if not exist "configs\default.yaml" (
    echo ERROR: Configuration file not found
    echo Expected: configs\default.yaml
    pause
    exit /b 1
)

echo Starting node daemon...
echo.
echo Configuration: configs\default.yaml
echo Logs: logs\node.log
echo.
echo Press Ctrl+C to stop the daemon
echo.

REM Start the daemon
python kernel\node_daemon.py --config configs\default.yaml

echo.
echo Daemon stopped.
pause

