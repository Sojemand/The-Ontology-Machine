@echo off
setlocal EnableExtensions
cd /d "%~dp0"

py -3 "%~dp0tools\build-runtime.py" --runtime %*
if not errorlevel 1 exit /b 0

python "%~dp0tools\build-runtime.py" --runtime %*
exit /b %ERRORLEVEL%
