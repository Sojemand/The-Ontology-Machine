@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_EXE="
for %%P in ("%~dp0.venv\python.exe" "%~dp0.venv\Scripts\python.exe" "%~dp0.venv\bin\python") do (
    if not defined PYTHON_EXE if exist "%%~fP" set "PYTHON_EXE=%%~fP"
)
if not defined PYTHON_EXE (
    echo Fehler: Entwicklungs-venv fehlt.
    echo Fuehre "%~dp0bootstrap.bat" aus.
    exit /b 1
)

"%PYTHON_EXE%" -V >nul 2>&1
if errorlevel 1 (
    echo Fehler: Entwicklungs-venv ist beschaedigt.
    echo Fuehre "%~dp0bootstrap.bat" aus.
    exit /b 1
)

"%PYTHON_EXE%" -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo Fehler: pytest fehlt in der Entwicklungs-venv.
    echo Fuehre "%~dp0bootstrap.bat" aus.
    exit /b 1
)

set "BASE_TEMP=%PYTEST_BASETEMP%"
if not defined BASE_TEMP (
    set "TEMP_ROOT=%TEMP%"
    if not defined TEMP_ROOT set "TEMP_ROOT=%TMP%"
    if not defined TEMP_ROOT set "TEMP_ROOT=%SystemDrive%\Temp"
    set "BASE_TEMP=%TEMP_ROOT%\om-cb-pytest-%RANDOM%%RANDOM%%RANDOM%"
)
if not exist "%BASE_TEMP%" mkdir "%BASE_TEMP%" >nul 2>&1

if "%~1"=="" (
    "%PYTHON_EXE%" -m pytest tests -q -m "not stress" --basetemp "%BASE_TEMP%"
) else (
    "%PYTHON_EXE%" -m pytest %* -q -m "not stress" --basetemp "%BASE_TEMP%"
)
exit /b %ERRORLEVEL%
