@echo off
title SHAR MP Admin Panel v3 Admin
cd /d "%~dp0"

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

python main.py
pause
