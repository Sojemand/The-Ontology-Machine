@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "RUNTIME_DIR=%~dp0runtime\python"
set "PYTHON_EXE="
for %%P in ("%RUNTIME_DIR%\python.exe" "%RUNTIME_DIR%\Scripts\python.exe" "%RUNTIME_DIR%\bin\python") do (
    if not defined PYTHON_EXE if exist "%%~fP" set "PYTHON_EXE=%%~fP"
)
if not defined PYTHON_EXE (
    echo {"ok": false, "error": "Bundled Python runtime is missing or damaged."}
    exit /b 1
)

set PYTHONDONTWRITEBYTECODE=1
set PYTHONNOUSERSITE=1
set "PYTHONHOME=%RUNTIME_DIR%"
set "PYTHONPATH="
if exist "%RUNTIME_DIR%\tcl\tcl8.6" set "TCL_LIBRARY=%RUNTIME_DIR%\tcl\tcl8.6"
if exist "%RUNTIME_DIR%\tcl\tk8.6" set "TK_LIBRARY=%RUNTIME_DIR%\tcl\tk8.6"
"%PYTHON_EXE%" -m edit_suite.bootstrap.runtime_report --root "%CD%" --mode startup %*
exit /b %ERRORLEVEL%
