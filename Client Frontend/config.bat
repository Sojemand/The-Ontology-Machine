@echo off
call "%~dp0runtime\launch-server.bat" config
exit /b %ERRORLEVEL%
