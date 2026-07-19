@echo off
REM ==============================================================
REM  High-Dimensional Data Explorer (v2) - Windows launcher
REM  Double-click this file to install requirements (first time
REM  only) and start the program.
REM ==============================================================

cd /d "%~dp0"

echo Checking for Python...

set PYTHON_CMD=

where python >nul 2>nul
if not errorlevel 1 set PYTHON_CMD=python

if not defined PYTHON_CMD (
    where py >nul 2>nul
    if not errorlevel 1 set PYTHON_CMD=py
)

if not defined PYTHON_CMD (
    echo.
    echo ERROR: Python was not found on this computer.
    echo Please install Python from https://www.python.org/downloads/
    echo During installation, make sure to check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo Found Python. Installing/checking required packages...

REM Try a normal install first. If it fails (e.g. no admin rights,
REM or a locked-down system Python), retry with --user instead of
REM leaving the user staring at a scary-looking error message.
%PYTHON_CMD% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo Standard install was blocked, retrying safely...
    %PYTHON_CMD% -m pip install -r requirements.txt --user --quiet
)
if errorlevel 1 (
    echo.
    echo Could not install packages automatically. Please run this manually:
    echo     %PYTHON_CMD% -m pip install -r requirements.txt --user
    echo.
    echo Attempting to start the program anyway in case packages are already installed...
)

echo.
echo Starting High-Dimensional Data Explorer...
echo.
%PYTHON_CMD% main.py

echo.
echo Program closed.
pause
