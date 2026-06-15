@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "BOOTSTRAP_PY="
for %%P in (
    "%~dp0..\..\04 - Normalizer\runtime\python\python.exe"
    "%~dp0..\..\06 - Edit Suite\runtime\python\python.exe"
    "%~dp0..\..\07 - MCP Server\runtime\python\python.exe"
    "%~dp0..\..\00 - Orchestrator\runtime\python\python.exe"
    "%~dp0..\..\01 - Optimizer\runtime\python\python.exe"
    "%~dp0..\..\02 - Interpreter\runtime\python\python.exe"
    "%~dp0..\..\03 - Validator\runtime\python\python.exe"
    "%~dp0..\..\05 - Corpus Builder\runtime\python\python.exe"
) do (
    if not defined BOOTSTRAP_PY if exist "%%~fP" set "BOOTSTRAP_PY=%%~fP"
)
if not defined BOOTSTRAP_PY (
    echo Fehler: Keine gebuendelte Runtime fuer den Tools-Dev-Test-Bootstrap gefunden.
    exit /b 1
)

"%BOOTSTRAP_PY%" "%~dp0..\bootstrap-dev-suite.py" --suite "%~dp0suite.json" %*
exit /b %ERRORLEVEL%
