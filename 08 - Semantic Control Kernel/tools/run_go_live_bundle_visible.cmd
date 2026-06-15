@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if "%~1"=="" (
    echo Usage: %~nx0 glv_YYYYMMDDHHMMSS [log_root]
    exit /b 1
)

set "MODULE_ROOT=%CD%"
set "RUN_ID=%~1"
set "LOG_ROOT=%MODULE_ROOT%\.tmp"
if not "%~2"=="" set "LOG_ROOT=%~f2"
if not exist "%LOG_ROOT%" mkdir "%LOG_ROOT%"

set "RUNNER_PYTHON=%MODULE_ROOT%\runtime\python\python.exe"
if not exist "%RUNNER_PYTHON%" set "RUNNER_PYTHON=%MODULE_ROOT%\dev-tests\.venv\python.exe"
if not exist "%RUNNER_PYTHON%" (
    echo Error: Missing runner Python at "%MODULE_ROOT%\runtime\python\python.exe" and "%MODULE_ROOT%\dev-tests\.venv\python.exe".
    echo Run build-runtime.bat or dev-tests\bootstrap.bat first.
    exit /b 1
)

set "STDOUT_LOG=%LOG_ROOT%\%RUN_ID%_visible_stdout.log"
set "STDERR_LOG=%LOG_ROOT%\%RUN_ID%_visible_stderr.log"

echo [GO-LIVE] run_id=%RUN_ID%
echo [GO-LIVE] stdout=%STDOUT_LOG%
echo [GO-LIVE] stderr=%STDERR_LOG%
echo [GO-LIVE] launching visible go-live bundle...

"%RUNNER_PYTHON%" "%MODULE_ROOT%\tools\visible_logged_runner.py" --cwd "%MODULE_ROOT%" --stdout-log "%STDOUT_LOG%" --stderr-log "%STDERR_LOG%" -- "%RUNNER_PYTHON%" "%MODULE_ROOT%\tools\generate_go_live_bundle.py" --run-id "%RUN_ID%"
exit /b %ERRORLEVEL%
