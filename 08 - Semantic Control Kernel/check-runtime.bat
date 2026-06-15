@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "RUNTIME_ROOT=%~dp0runtime\python"
set "RUNTIME_PYTHON=%RUNTIME_ROOT%\python.exe"

if not exist "%RUNTIME_PYTHON%" (
    echo {"ok":false,"status":"error","module_key":"semantic_control_kernel","error":{"code":"runtime_missing","message":"Runtime Python is missing. Run build-runtime.bat first."}}
    exit /b 1
)

set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONNOUSERSITE=1"
set "PYTHONHOME=%RUNTIME_ROOT%"
set "PYTHONPATH="

"%RUNTIME_PYTHON%" -m semantic_control_kernel.bootstrap.runtime_report --root "%~dp0." --strict
exit /b %ERRORLEVEL%
