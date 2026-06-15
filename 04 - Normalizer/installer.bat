@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tools\installer.ps1" %*
exit /b %ERRORLEVEL%
