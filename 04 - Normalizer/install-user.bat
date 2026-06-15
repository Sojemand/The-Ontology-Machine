@echo off
setlocal EnableExtensions
call "%~dp0installer.bat" %*
exit /b %ERRORLEVEL%
