@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_EXE="
for %%P in ("%~dp0.venv\python.exe" "%~dp0.venv\Scripts\python.exe" "%~dp0.venv\bin\python") do (
    if not defined PYTHON_EXE if exist "%%~fP" set "PYTHON_EXE=%%~fP"
)
if not defined PYTHON_EXE (
    echo Error: development venv is missing.
    echo Run "%~dp0bootstrap.bat".
    exit /b 1
)

"%PYTHON_EXE%" -V >nul 2>&1
if errorlevel 1 (
    echo Error: development venv is damaged.
    echo Run "%~dp0bootstrap.bat".
    exit /b 1
)

"%PYTHON_EXE%" -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo Error: pytest is missing from the development venv.
    echo Run "%~dp0bootstrap.bat".
    exit /b 1
)

if "%~1"=="" (
    "%PYTHON_EXE%" -m pytest tests -q
) else (
    "%PYTHON_EXE%" -m pytest %* -q
)
exit /b %ERRORLEVEL%
