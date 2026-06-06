@echo off
chcp 936 >nul
title English Learning - Restart Service

echo ====================================
echo   English Learning - Restart Service
echo ====================================
echo.

cd /d "%~dp0"

:: Kill old process on port 8082
echo [1/2] Stopping old service...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8082 ^| findstr LISTENING') do (
    if not "%%a"=="" (
        echo     Found PID: %%a
        taskkill /f /pid %%a >nul 2>&1
        timeout /t 2 /nobreak >nul
    )
)

:check_port
netstat -ano | findstr :8082 | findstr LISTENING >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto check_port
)
echo     Port 8082 released.
echo.

:: Start Flask in the same window (visible logs)
echo [2/2] Starting service...
echo.
echo ------------------------------------------------------------
echo  Server will start below. Close this window to stop.
echo  Access at: http://localhost:8082
echo ------------------------------------------------------------
echo.

set PYTHON_PATH="C:\Users\ADMIN\AppData\Local\Programs\Python\Python311\python.exe"
%PYTHON_PATH% app.py

:: If we get here, Flask stopped or failed
echo.
echo ====================================
echo   Service stopped.
echo   Close this window or press any key.
echo ====================================
pause >nul
