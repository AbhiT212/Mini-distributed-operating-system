@echo off
REM Start MiniDOS Interactive Shell

echo ========================================
echo   MiniDOS Interactive Shell
echo ========================================
echo.

REM Change to project root
cd /d "%~dp0.."

REM Check if Python is available
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Starting shell...
echo.
echo Connecting to: localhost:9000
echo.
echo Make sure the node daemon is running!
echo If not, start it with: scripts\start_node.bat
echo.

REM Start the shell
python cli\minishell.py --host localhost --port 9000

echo.
pause

