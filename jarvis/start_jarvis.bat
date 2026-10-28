@echo off
cd /d "%~dp0"

:: Launch JARVIS with pythonw (no console window)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" main.py
    exit /b
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    start "" py -3.11 -m pythonw main.py 2>nul || start "" py -3.11 main.py
    exit /b
)

where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw main.py
    exit /b
)

start "" python main.py
exit /b
