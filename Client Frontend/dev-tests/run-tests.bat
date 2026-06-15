@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if not exist "%CD%\node\node.exe" (
    echo Fehler: Gebuendeltes Node fehlt unter "%CD%\node\node.exe".
    exit /b 1
)

if "%~1"=="" (
    set "POWERSHELL_BIN="
    for %%P in (
        "%CD%\runtime\powershell\pwsh.exe"
        "%CD%\runtime\powershell\powershell.exe"
        "%CD%\runtime\powershell\pwsh\pwsh.exe"
    ) do (
        if not defined POWERSHELL_BIN if exist "%%~P" set "POWERSHELL_BIN=%%~fP"
    )
    if not defined POWERSHELL_BIN (
        echo Fehler: Gebuendelte PowerShell fehlt unter "%CD%\runtime\powershell".
        exit /b 1
    )
    "!POWERSHELL_BIN!" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%CD%\dev-tests\deploy-installer-roundtrip.ps1"
    if errorlevel 1 exit /b %ERRORLEVEL%
)

"%CD%\node\node.exe" --disable-warning=ExperimentalWarning --test --test-isolation=none --test-reporter=spec %*
exit /b %ERRORLEVEL%
