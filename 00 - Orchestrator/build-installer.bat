@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "SCRIPT=%~dp0..\tools\build-installer.py"
set "SOURCE_PYTHON=%LocalAppData%\Programs\Python\Python311\python.exe"

if not exist "%SOURCE_PYTHON%" goto fallback_python
"%SOURCE_PYTHON%" "%SCRIPT%" --module "00 - Orchestrator" --source-python "%SOURCE_PYTHON%" %*
exit /b !ERRORLEVEL!

:fallback_python
py -3.11 "%SCRIPT%" --module "00 - Orchestrator" %*
if not errorlevel 1 exit /b 0

python "%SCRIPT%" --module "00 - Orchestrator" %*
exit /b %ERRORLEVEL%
