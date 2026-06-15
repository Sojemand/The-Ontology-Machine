from __future__ import annotations

# cspell:words LOCALAPPDATA setlocal

from all_in_one_config import CHECK_RUNTIME_MODULES
from all_in_one_uninstall_script import UNINSTALL_POWERSHELL


def check_all_runtimes_batch() -> str:
    module_checks = "\n".join(f'call :check_module "{module_name}"' for module_name in CHECK_RUNTIME_MODULES)
    return f"""@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "FAILED=0"

{module_checks}
call :check_client_frontend

echo.
if "%FAILED%"=="0" (
    echo All runtime checks passed.
) else (
    echo One or more runtime checks failed.
)
exit /b %FAILED%

:check_module
echo.
echo === %~1 ===
if not exist "%~dp0%~1\\check-runtime.bat" (
    echo Missing check-runtime.bat for %~1
    set "FAILED=1"
    exit /b 0
)
call "%~dp0%~1\\check-runtime.bat"
if errorlevel 1 set "FAILED=1"
exit /b 0

:check_client_frontend
echo.
echo === Client Frontend ===
if not exist "%~dp0Client Frontend\\node\\node.exe" (
    echo Missing bundled Node runtime.
    set "FAILED=1"
    exit /b 0
)
call "%~dp0Client Frontend\\node\\node.exe" --disable-warning=ExperimentalWarning "%~dp0Client Frontend\\tools\\check-runtimes.mjs"
if errorlevel 1 set "FAILED=1"
exit /b 0
"""


def uninstall_launcher_batch() -> str:
    return """@echo off
setlocal EnableExtensions EnableDelayedExpansion
for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "SCRIPT=%ROOT%\\Uninstall Ontology Machine.ps1"

if not exist "%SCRIPT%" (
    echo Uninstall script missing: "%SCRIPT%"
    pause
    exit /b 1
)

set "TEMP_SCRIPT=%TEMP%\\OntologyMachine-Uninstall-%RANDOM%-%RANDOM%.ps1"
copy /Y "%SCRIPT%" "%TEMP_SCRIPT%" >nul
if errorlevel 1 (
    echo Could not prepare uninstall script.
    pause
    exit /b 1
)

start "Ontology Machine Uninstaller" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TEMP_SCRIPT%" -InstallRoot "%ROOT%"
exit /b 0
"""


def uninstall_powershell() -> str:
    return UNINSTALL_POWERSHELL


def root_readme() -> str:
    return """Ontology Machine all-in-one install

Installed layout:
- 00 - Orchestrator through 08 - Semantic Control Kernel stay as sibling modules.
- Client Frontend is installed beside the modules and keeps its mutable app home under LOCALAPPDATA\\Enterprise Stack\\Client Frontend.
- SampleDB is installed beside the modules and contains bundled demo/sample Artifact Trees.
- Extractor_Tools is installed beside the modules and contains optional input-preparation helpers.
- The Machine Doku PDF is installed beside the modules and contains the Quickstart Handbook PDF.

Entry points:
- Start Orchestrator.bat
- Start Client Frontend.bat
- Configure Client Frontend.bat
- Start Article Archive Extractor.bat
- Start YouTube Transcript Extractor.bat
- Start Audio Transcription Extractor.bat
- Uninstall Ontology Machine.bat

Install defaults:
- Fresh Client Frontend config resolves its first corpus DB from the install root: SampleDB\\Consciousness Travel - Default Demo\\Corpus\\corpus.db.
- Orchestrator state is not seeded by the installer; create or select Artifact Trees from the Orchestrator/Kernel workflow.
- Existing user-selected Frontend DB state is preserved on upgrade.
- Extractor_Tools contains small local sidecars for turning article URLs, YouTube subtitles and local audio/video transcripts into Markdown files for later ingestion.

The installer preserves module state/config on upgrade. Use Uninstall Ontology Machine.bat for a clean removal of the install root and the Client Frontend app home.
"""
