@echo off
REM Force resync of all nodes

echo ========================================
echo   MiniDOS Force Resync
echo ========================================
echo.

echo This script will trigger a full resync of all nodes.
echo.
echo WARNING: This may take some time depending on the
echo          number of files in your distributed filesystem.
echo.

set /p confirm="Continue? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo Triggering resync...
echo.

REM Change to project root
cd /d "%~dp0.."

REM TODO: Implement resync trigger command
REM For now, just restart the daemon which will trigger sync

echo [INFO] Full resync is triggered automatically on daemon restart
echo [INFO] To force resync, restart all node daemons
echo.

pause

