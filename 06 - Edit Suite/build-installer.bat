@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "SCRIPT=%~dp0..\tools\build-installer.py"
set "SOURCE_PYTHON=%LocalAppData%\Programs\Python\Python311\python.exe"

if not exist "%SOURCE_PYTHON%" goto fallback_python
"%SOURCE_PYTHON%" "%SCRIPT%" --module "06 - Edit Suite" --source-python "%SOURCE_PYTHON%" %*
exit /b !ERRORLEVEL!

:fallback_python
py -3.11 "%SCRIPT%" --module "06 - Edit Suite" %*
if not errorlevel 1 exit /b 0

python "%SCRIPT%" --module "06 - Edit Suite" %*
exit /b %ERRORLEVEL%
