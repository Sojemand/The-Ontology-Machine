@echo off
setlocal EnableExtensions
cd /d "%~dp0"

call "%~dp0..\tools\build-runtimes.bat" --module "06 - Edit Suite" %*
exit /b %ERRORLEVEL%
