@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
for %%I in ("%ROOT%..\..") do set "MACHINE_ROOT=%%~fI"
set "PYTHON_EXE="

for %%P in (
    "%ROOT%.venv\Scripts\python.exe"
    "%MACHINE_ROOT%\00 - Orchestrator\runtime\python\python.exe"
    "%MACHINE_ROOT%\06 - Edit Suite\runtime\python\python.exe"
    "%MACHINE_ROOT%\Client Frontend\runtime\python\python.exe"
) do (
    if not defined PYTHON_EXE if exist "%%~fP" set "PYTHON_EXE=%%~fP"
)

if not defined PYTHON_EXE (
    echo Bundled Python runtime was not found.
    echo The "YouTube Transcript Extractor" folder must stay inside the Ontology Machine Extractor_Tools folder.
    echo Expected for example:
    echo "%MACHINE_ROOT%\00 - Orchestrator\runtime\python\python.exe"
    pause
    exit /b 1
)

start "YouTube Transcript Extractor" "%PYTHON_EXE%" "%ROOT%youtube_transcript_extractor.py"
exit /b 0
