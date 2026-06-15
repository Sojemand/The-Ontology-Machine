@echo off
call "%~dp0runtime\launch-server.bat" chat
exit /b %ERRORLEVEL%
