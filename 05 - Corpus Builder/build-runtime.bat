@echo off
setlocal EnableExtensions
cd /d "%~dp0"
call "%~dp0..\tools\build-runtimes.bat" --module "05 - Corpus Builder" --offline %*
exit /b %ERRORLEVEL%
