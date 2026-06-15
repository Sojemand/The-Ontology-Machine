@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "BOOTSTRAP_PY="
for %%P in ("%~dp0..\runtime\python\python.exe" "%~dp0..\runtime\python\Scripts\python.exe" "%~dp0..\runtime\python\bin\python") do (
    if not defined BOOTSTRAP_PY if exist "%%~fP" set "BOOTSTRAP_PY=%%~fP"
)
if not defined BOOTSTRAP_PY (
    echo Fehler: Gebuendelte Runtime fuer den Dev-Test-Bootstrap fehlt.
    exit /b 1
)

"%BOOTSTRAP_PY%" "%~dp0..\..\tools\bootstrap-dev-suite.py" --suite "%~dp0suite.json" %*
exit /b %ERRORLEVEL%
