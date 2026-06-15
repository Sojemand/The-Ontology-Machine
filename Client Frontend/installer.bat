@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "POWERSHELL_BIN="

for %%P in (
    "%ROOT%runtime\powershell\pwsh.exe"
    "%ROOT%runtime\powershell\powershell.exe"
    "%ROOT%runtime\powershell\pwsh\pwsh.exe"
) do (
    if not defined POWERSHELL_BIN if exist %%~P set "POWERSHELL_BIN=%%~fP"
)

if not defined POWERSHELL_BIN (
    echo {"ok":false,"error":"Bundled PowerShell runtime fehlt oder ist beschaedigt.","expected":"runtime\\powershell\\pwsh.exe"}
    exit /b 1
)

"%POWERSHELL_BIN%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%ROOT%tools\installer.ps1" %*
exit /b %ERRORLEVEL%
