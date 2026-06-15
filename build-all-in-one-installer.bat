@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "PYTHON_EXE="

for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles(x86)%\Python311\python.exe"
) do (
    if not defined PYTHON_EXE if exist "%%~fP" set "PYTHON_EXE=%%~fP"
)

if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('py -3.11 -c "import sys; print(sys.executable)" 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%~fP"
    )
)

if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('where python.exe 2^>nul') do (
        if not defined PYTHON_EXE (
            "%%~fP" -c "import sys; v=sys.version_info; assert v.major == 3 and v.minor == 11" ^>nul 2^>nul
            if not errorlevel 1 set "PYTHON_EXE=%%~fP"
        )
    )
)

if not defined PYTHON_EXE (
    echo Python 3.11 wurde nicht gefunden.
    exit /b 1
)

"%PYTHON_EXE%" "%ROOT%tools\build-all-in-one-installer.py" %*
exit /b !ERRORLEVEL!
