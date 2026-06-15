@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "SCRIPT=%~dp0build-runtimes.py"
set "SOURCE_PYTHON=%LocalAppData%\Programs\Python\Python311\python.exe"

if exist "%SOURCE_PYTHON%" (
    "%SOURCE_PYTHON%" "%SCRIPT%" --python "%SOURCE_PYTHON%" %*
    exit /b !ERRORLEVEL!
)

py -3.11 "%SCRIPT%" %*
if not errorlevel 1 exit /b 0

for /f "delims=" %%P in ('where python.exe 2^>nul') do (
    if not defined SOURCE_PYTHON_FALLBACK (
        "%%~fP" -c "import sys; v=sys.version_info; assert v.major == 3 and v.minor == 11" ^>nul 2^>nul
        if not errorlevel 1 set "SOURCE_PYTHON_FALLBACK=%%~fP"
    )
)

if not defined SOURCE_PYTHON_FALLBACK (
    echo Python 3.11 wurde nicht gefunden.
    exit /b 1
)

"%SOURCE_PYTHON_FALLBACK%" "%SCRIPT%" --python "%SOURCE_PYTHON_FALLBACK%" %*
exit /b !ERRORLEVEL!
