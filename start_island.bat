@echo off
cd /d "%~dp0"

if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" main.py island
    exit /b
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    start "" py -3.11 main.py island
    exit /b
)

start "" pythonw main.py island
