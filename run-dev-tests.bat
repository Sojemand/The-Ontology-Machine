@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LAUNCHER_PYTHON="
for %%P in (
    "%~dp004 - Normalizer\runtime\python\python.exe"
    "%~dp006 - Edit Suite\runtime\python\python.exe"
    "%~dp007 - MCP Server\runtime\python\python.exe"
    "%~dp008 - Semantic Control Kernel\runtime\python\python.exe"
    "%~dp000 - Orchestrator\runtime\python\python.exe"
    "%~dp001 - Optimizer\runtime\python\python.exe"
    "%~dp002 - Interpreter\runtime\python\python.exe"
    "%~dp003 - Validator\runtime\python\python.exe"
    "%~dp005 - Corpus Builder\runtime\python\python.exe"
) do (
    if not defined LAUNCHER_PYTHON if exist "%%~fP" set "LAUNCHER_PYTHON=%%~fP"
)

if not defined LAUNCHER_PYTHON (
    echo Fehler: Keine gebuendelte Python-Runtime fuer den Root-Dispatcher gefunden.
    exit /b 1
)

"%LAUNCHER_PYTHON%" "%~dp0tools\run-dev-tests.py" %*
exit /b %ERRORLEVEL%
