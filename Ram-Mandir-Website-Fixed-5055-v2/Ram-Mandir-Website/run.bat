@echo off
title Ram Mandir Visitor Portal
cd /d "%~dp0"

echo ========================================================
echo   RAM MANDIR VISITOR PORTAL
echo ========================================================
echo.

set PY=
where py >nul 2>nul && set PY=py
if not defined PY (
    where python >nul 2>nul && set PY=python
)

if not defined PY (
    echo  ERROR: Python was not found on this computer.
    echo.
    echo  Install it from https://www.python.org/downloads/
    echo  IMPORTANT: tick "Add Python to PATH" during setup,
    echo  then run this file again.
    echo.
    pause
    exit /b 1
)

echo  Checking Flask is installed...
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo.
    echo  Could not install Flask. Check your internet connection.
    echo.
    pause
    exit /b 1
)

echo.
echo  Starting the server.
echo.
echo      Open this address in your browser:
echo          http://127.0.0.1:5055
echo.
echo      Press Ctrl+C to stop.
echo.

%PY% app.py

echo.
echo  The server has stopped.
pause
