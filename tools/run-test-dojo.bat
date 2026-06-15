@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

set "LAUNCHER_PYTHON="
for %%P in (
    "%~dp0..\06 - Edit Suite\runtime\python\python.exe"
    "%~dp0..\00 - Orchestrator\runtime\python\python.exe"
    "%~dp0..\07 - MCP Server\runtime\python\python.exe"
    "%~dp0..\04 - Normalizer\runtime\python\python.exe"
    "%~dp0..\05 - Corpus Builder\runtime\python\python.exe"
    "%~dp0..\01 - Optimizer\runtime\python\python.exe"
    "%~dp0..\02 - Interpreter\runtime\python\python.exe"
    "%~dp0..\03 - Validator\runtime\python\python.exe"
) do (
    if not defined LAUNCHER_PYTHON if exist "%%~fP" set "LAUNCHER_PYTHON=%%~fP"
)

if not defined LAUNCHER_PYTHON (
    echo Fehler: Keine gebuendelte Python-Runtime fuer das Test Dojo gefunden.
    exit /b 1
)

pushd "%~dp0test-dojo"
"%LAUNCHER_PYTHON%" -m dojo %*
set "DOJO_EXIT=%ERRORLEVEL%"
popd
exit /b %DOJO_EXIT%
