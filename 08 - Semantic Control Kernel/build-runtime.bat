@echo off
setlocal EnableExtensions
call "%~dp0..\tools\build-runtimes.bat" --module "08 - Semantic Control Kernel" %*
exit /b %ERRORLEVEL%
