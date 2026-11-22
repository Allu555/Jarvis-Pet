@echo off
title JARVIS 3D Spider Drone
cd /d "%~dp0jarvis\spider_3d"

set "PYW=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if exist "%PYW%" (
    start "" "%PYW%" "%~dp0jarvis\spider_3d\app.py"
    exit /b
)

if exist "%PY%" (
    start "" "%PY%" "%~dp0jarvis\spider_3d\app.py"
    exit /b
)

pythonw "%~dp0jarvis\spider_3d\app.py"
