@echo off
cd /d "%~dp0"
echo Creating JARVIS Desktop Shortcut...

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3.11 create_jarvis_shortcut.py
    pause
    exit /b
)

python create_jarvis_shortcut.py
pause
