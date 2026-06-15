@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "RUNTIME_DIR=%~dp0runtime\python"
set "PYTHON_EXE="
for %%P in ("%RUNTIME_DIR%\python.exe" "%RUNTIME_DIR%\Scripts\python.exe" "%RUNTIME_DIR%\bin\python") do (
    if not defined PYTHON_EXE if exist "%%~fP" set "PYTHON_EXE=%%~fP"
)
if not defined PYTHON_EXE (
    echo Error: Bundled Python runtime is missing or damaged.
    echo Erwartet unter "%RUNTIME_DIR%".
    echo Run "%~dp0build-runtime.bat".
    exit /b 1
)

set PYTHONDONTWRITEBYTECODE=1
set PYTHONNOUSERSITE=1
set "PYTHONHOME=%RUNTIME_DIR%"
set "PYTHONPATH="
if exist "%RUNTIME_DIR%\tcl\tcl8.6" set "TCL_LIBRARY=%RUNTIME_DIR%\tcl\tcl8.6"
if exist "%RUNTIME_DIR%\tcl\tk8.6" set "TK_LIBRARY=%RUNTIME_DIR%\tcl\tk8.6"

set "PREFLIGHT_REPORT=%TEMP%\edit-suite-runtime-%RANDOM%.json"
"%PYTHON_EXE%" -m edit_suite.bootstrap.runtime_report --root "%CD%" --mode runtime > "%PREFLIGHT_REPORT%"
if errorlevel 1 (
    type "%PREFLIGHT_REPORT%"
    del "%PREFLIGHT_REPORT%" >nul 2>nul
    echo.
    echo Error: Runtime preflight failed.
    pause
    exit /b 1
)
del "%PREFLIGHT_REPORT%" >nul 2>nul
"%PYTHON_EXE%" -m edit_suite
if errorlevel 1 (
    echo.
    echo Startup failed. See the message above.
    pause
)
