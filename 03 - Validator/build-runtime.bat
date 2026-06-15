@echo off
setlocal EnableExtensions
cd /d "%~dp0"
call "%~dp0..\tools\build-runtimes.bat" --module "03 - Validator" --offline %*
exit /b %ERRORLEVEL%
