@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_EXE="
for %%P in ("%~dp0.venv\python.exe" "%~dp0.venv\Scripts\python.exe" "%~dp0.venv\bin\python") do (
    if not defined PYTHON_EXE if exist "%%~fP" set "PYTHON_EXE=%%~fP"
)
if not defined PYTHON_EXE (
    echo Error: Development venv is missing.
    echo Run "%~dp0bootstrap.bat".
    exit /b 1
)

"%PYTHON_EXE%" -m pytest tests -q %*
exit /b %ERRORLEVEL%
