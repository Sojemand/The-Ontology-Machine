@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
for %%I in ("%ROOT%..\..") do set "MACHINE_ROOT=%%~fI"
set "BASE_PYTHON="
set "VENV_PYTHON=%ROOT%.venv\Scripts\python.exe"

for %%P in (
    "%MACHINE_ROOT%\00 - Orchestrator\runtime\python\python.exe"
    "%MACHINE_ROOT%\06 - Edit Suite\runtime\python\python.exe"
    "%MACHINE_ROOT%\Client Frontend\runtime\python\python.exe"
) do (
    if not defined BASE_PYTHON if exist "%%~fP" set "BASE_PYTHON=%%~fP"
)

if not defined BASE_PYTHON (
    echo Bundled Python runtime was not found.
    echo The "Article Archive Extractor" folder must stay inside the Ontology Machine Extractor_Tools folder.
    echo Expected for example:
    echo "%MACHINE_ROOT%\00 - Orchestrator\runtime\python\python.exe"
    pause
    exit /b 1
)

if not exist "%VENV_PYTHON%" (
    echo Creating local extractor environment...
    "%BASE_PYTHON%" -m venv "%ROOT%.venv"
    if errorlevel 1 (
        echo Failed to create the local extractor environment.
        pause
        exit /b 1
    )
)

echo Installing optional article extractor dependency...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to update pip.
    pause
    exit /b 1
)

"%VENV_PYTHON%" -m pip install -r "%ROOT%requirements.txt"
if errorlevel 1 (
    echo Failed to install optional dependencies.
    pause
    exit /b 1
)

echo.
echo Done. Restart "Start Article Archive Extractor.bat".
pause
exit /b 0
