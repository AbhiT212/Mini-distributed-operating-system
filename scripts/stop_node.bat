@echo off
REM Stop MiniDOS Node Daemon

echo ========================================
echo   Stopping MiniDOS Node Daemon
echo ========================================
echo.

REM Find and kill Python processes running node_daemon.py
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID:"') do (
    wmic process where "ProcessId=%%a" get CommandLine /format:list 2>nul | find "node_daemon.py" >nul
    if not errorlevel 1 (
        echo Stopping process %%a...
        taskkill /PID %%a /F >nul 2>&1
        if not errorlevel 1 (
            echo [OK] Process %%a stopped
        )
    )
)

echo.
echo Done.
pause

