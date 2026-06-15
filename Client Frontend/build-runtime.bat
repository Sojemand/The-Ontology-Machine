@echo off
call "%~dp0..\tools\build-runtimes.bat" --module "Client Frontend" --offline %*
exit /b %ERRORLEVEL%
