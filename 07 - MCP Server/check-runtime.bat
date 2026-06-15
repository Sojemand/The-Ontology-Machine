@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "RUNTIME_DIR=%~dp0runtime\python"
set "PYTHON_EXE="
for %%P in ("%RUNTIME_DIR%\python.exe" "%RUNTIME_DIR%\Scripts\python.exe" "%RUNTIME_DIR%\bin\python") do (
    if not defined PYTHON_EXE if exist "%%~fP" set "PYTHON_EXE=%%~fP"
)
if not defined PYTHON_EXE (
    echo {"ok": false, "error": "Gebuendelte Python-Runtime fehlt oder ist beschaedigt."}
    exit /b 1
)

set PYTHONDONTWRITEBYTECODE=1
set PYTHONNOUSERSITE=1
set "PYTHONHOME=%RUNTIME_DIR%"
set "PYTHONPATH="
"%PYTHON_EXE%" -m mcp_server.orchestrator_contract --healthcheck
exit /b %ERRORLEVEL%
