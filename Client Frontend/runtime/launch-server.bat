@echo off
setlocal EnableExtensions

set "MODE=%~1"
if /I not "%MODE%"=="config" set "MODE=chat"

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
if defined VISION_PIPELINE_CLIENT_FRONTEND_HOME (
    set "APP_HOME=%VISION_PIPELINE_CLIENT_FRONTEND_HOME%"
) else if defined LOCALAPPDATA (
    set "APP_HOME=%LOCALAPPDATA%\Enterprise Stack\Client Frontend"
) else (
    echo [startup] VISION_PIPELINE_CLIENT_FRONTEND_HOME ist nicht gesetzt und LOCALAPPDATA fehlt. 1>&2
    exit /b 1
)

set "LOG_DIR=%APP_HOME%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
call :new_session_id

if /I "%MODE%"=="config" (
    set "APP_NAME=Sachbearbeiter Konfiguration"
    set "CONSOLE_TITLE=Frontend Server Konfiguration"
    set "LOG_FILE=%LOG_DIR%\config-startup.log"
    set "BROWSER_LOG_FILE=%LOG_DIR%\config-browser-helper.log"
    set "SERVER_ARGS=--config"
    set "SERVER_PORT=3001"
    set "SERVER_STATE_FILE=%APP_HOME%\state\server-config.json"
    set "OPEN_URL=http://127.0.0.1:3001/config"
) else (
    set "APP_NAME=Sachbearbeiter"
    set "CONSOLE_TITLE=Frontend Server"
    set "LOG_FILE=%LOG_DIR%\startup.log"
    set "BROWSER_LOG_FILE=%LOG_DIR%\startup-browser-helper.log"
    set "SERVER_ARGS="
    set "SERVER_PORT=3000"
    set "SERVER_STATE_FILE=%APP_HOME%\state\server-chat.json"
    set "OPEN_URL=http://127.0.0.1:3000"
)

title %CONSOLE_TITLE%

set "NODE_BIN=%ROOT%\node\node.exe"
set "POWERSHELL_BIN="
for %%P in (
    "%ROOT%\runtime\powershell\pwsh.exe"
    "%ROOT%\runtime\powershell\powershell.exe"
    "%ROOT%\runtime\powershell\pwsh\pwsh.exe"
) do (
    if not defined POWERSHELL_BIN if exist "%%~P" set "POWERSHELL_BIN=%%~fP"
)
set "CHECKER=%ROOT%\tools\check-runtimes.mjs"
set "SERVER_ENTRY=%ROOT%\server\index.js"
set "PORT_CLEANER=%ROOT%\tools\clear-stale-server-port.mjs"

>"%LOG_FILE%" echo [%date% %time%] Starting %APP_NAME%.
echo [%SESSION_ID%] %APP_NAME% startet. Server-Log: "%LOG_FILE%"
call :log "Working directory: %ROOT%"
call :log "App home: %APP_HOME%"
call :log "Session ID: %SESSION_ID%"
call :log "Expected URL: %OPEN_URL%"

if not exist "%NODE_BIN%" (
    call :log "Bundled Node runtime fehlt oder ist beschaedigt: %NODE_BIN%"
    set "FAIL_MESSAGE=[%SESSION_ID%] Bundled Node runtime fehlt. Details: %LOG_FILE%"
    goto :fail
)

call :log "Checking bundled runtimes via %CHECKER%."
"%NODE_BIN%" --disable-warning=ExperimentalWarning "%CHECKER%" >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    call :log "Bundled runtime check failed."
    set "FAIL_MESSAGE=[%SESSION_ID%] Runtime-Check fehlgeschlagen. Details: %LOG_FILE%"
    goto :fail
)

if not defined POWERSHELL_BIN (
    call :log "Bundled PowerShell runtime fehlt oder ist beschaedigt."
    set "FAIL_MESSAGE=[%SESSION_ID%] Bundled PowerShell runtime fehlt. Details: %LOG_FILE%"
    goto :fail
)

if not exist "%PORT_CLEANER%" (
    call :log "Port cleaner fehlt oder ist beschaedigt: %PORT_CLEANER%"
    set "FAIL_MESSAGE=[%SESSION_ID%] Port-Bereiniger fehlt. Details: %LOG_FILE%"
    goto :fail
)

call :log "Checking for stale %APP_NAME% server process on port %SERVER_PORT%."
"%NODE_BIN%" --disable-warning=ExperimentalWarning "%PORT_CLEANER%" --port "%SERVER_PORT%" --allowed-exe "%NODE_BIN%" --server-state-file "%SERVER_STATE_FILE%" --powershell "%POWERSHELL_BIN%" --log-file "%LOG_FILE%" --session-id "%SESSION_ID%"
if errorlevel 1 (
    call :log "Stale server cleanup failed."
    set "FAIL_MESSAGE=[%SESSION_ID%] Port %SERVER_PORT% konnte nicht freigegeben werden. Details: %LOG_FILE%"
    goto :fail
)

call :log "Browser wird erst nach erfolgreichem Serverstart fuer %OPEN_URL% geoeffnet."
call :log "Launching server entry %SERVER_ENTRY% %SERVER_ARGS%"
if defined SERVER_ARGS (
    set "VISION_PIPELINE_CLIENT_FRONTEND_HOME=%APP_HOME%"
    "%NODE_BIN%" --disable-warning=ExperimentalWarning "%SERVER_ENTRY%" %SERVER_ARGS% --open-browser-url "%OPEN_URL%" --browser-log-file "%BROWSER_LOG_FILE%" --session-id "%SESSION_ID%" >>"%LOG_FILE%" 2>&1
) else (
    set "VISION_PIPELINE_CLIENT_FRONTEND_HOME=%APP_HOME%"
    "%NODE_BIN%" --disable-warning=ExperimentalWarning "%SERVER_ENTRY%" --open-browser-url "%OPEN_URL%" --browser-log-file "%BROWSER_LOG_FILE%" --session-id "%SESSION_ID%" >>"%LOG_FILE%" 2>&1
)

set "EXIT_CODE=%ERRORLEVEL%"
call :log "Server exited with code %EXIT_CODE%."
if not "%EXIT_CODE%"=="0" (
    set "FAIL_MESSAGE=[%SESSION_ID%] Serverstart fehlgeschlagen. Details: %LOG_FILE%"
    goto :fail
)
exit /b %EXIT_CODE%

:log
echo [%SESSION_ID%] %~1
>>"%LOG_FILE%" echo [%date% %time%] [%SESSION_ID%] %~1
exit /b 0

:fail
echo %FAIL_MESSAGE% 1>&2
if defined LOG_FILE if exist "%LOG_FILE%" (
    echo.
    echo ===== Startprotokoll =====
    type "%LOG_FILE%"
)
echo.
echo [%SESSION_ID%] Die Konsole bleibt offen, damit der Fehler sichtbar bleibt.
pause >nul
exit /b 1

:new_session_id
set "SESSION_ID=%DATE%_%TIME%_%RANDOM%%RANDOM%"
set "SESSION_ID=%SESSION_ID: =0%"
set "SESSION_ID=%SESSION_ID:/=-%"
set "SESSION_ID=%SESSION_ID::=-%"
set "SESSION_ID=%SESSION_ID:.=-%"
set "SESSION_ID=%SESSION_ID:,=-%"
exit /b 0
