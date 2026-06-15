@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if not exist "%CD%\node\node.exe" (
    echo Fehler: Gebuendeltes Node fehlt unter "%CD%\node\node.exe".
    exit /b 1
)
if not exist "%CD%\node_modules" (
    echo Fehler: node_modules fehlt. Die Frontend-Dev-Test-Suite nutzt die lokale Offline-Installation im Modulroot.
    exit /b 1
)

echo Frontend Dev-Test-Suite ist bereit.
exit /b 0
