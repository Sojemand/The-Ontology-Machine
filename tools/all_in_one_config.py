from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

from installer_config import InstallerConfig, load_installer_config

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_APP_VERSION = date.today().isoformat()
MODULE_DIRS = (
    "00 - Orchestrator",
    "01 - Optimizer",
    "02 - Interpreter",
    "03 - Validator",
    "04 - Normalizer",
    "05 - Corpus Builder",
    "06 - Edit Suite",
    "07 - MCP Server",
    "08 - Semantic Control Kernel",
    "Client Frontend",
)
ROOT_PAYLOAD_DIRS = ("SampleDB", "Extractor_Tools", "The Machine Doku PDF")
CLIENT_FRONTEND_MODULE = "Client Frontend"
DEFAULT_DEMO_ARTIFACT_TREE = r"SampleDB\Consciousness Travel - Default Demo"
DEFAULT_DEMO_DB_PATH = DEFAULT_DEMO_ARTIFACT_TREE + r"\Corpus\corpus.db"
CLIENT_FRONTEND_IMMUTABLE_DIRS = (
    "app",
    "assistant",
    "client_frontend",
    "node",
    "runtime",
    "server",
    "shared",
)
CLIENT_FRONTEND_IMMUTABLE_FILES = (
    "package.json",
    "start.bat",
    "config.bat",
    "installer.bat",
    "build-runtime.bat",
    "README.md",
    "README.txt",
    "requirements.txt",
    "tools/check-runtimes.mjs",
    "tools/clear-stale-server-port.mjs",
    "tools/deploy.ps1",
    "tools/installer.ps1",
)
INSTALLER_ICON_FILES = (
    "ontology-machine.ico",
    "orchestrator.ico",
    "client-frontend.ico",
    "frontend-config.ico",
    "article-extractor.ico",
    "youtube-transcript.ico",
    "audio-transcription.ico",
)
MODULE_MUTABLE_DIR_OVERRIDES = {
    "07 - MCP Server": ("state", "logs", "output", "runtime\\state"),
    "08 - Semantic Control Kernel": ("state", "logs", "output", "runtime\\state"),
}
MODULE_MUTABLE_FILE_OVERRIDES = {
    "07 - MCP Server": ("state\\semantic_control_kernel_host_bridge.log",),
}
MODULE_MUTABLE_FILE_REPLACEMENTS = {
    "04 - Normalizer": (),
}
CHECK_RUNTIME_MODULES = (
    "00 - Orchestrator",
    "01 - Optimizer",
    "02 - Interpreter",
    "03 - Validator",
    "04 - Normalizer",
    "05 - Corpus Builder",
    "06 - Edit Suite",
    "07 - MCP Server",
    "08 - Semantic Control Kernel",
)


def default_stage_dir() -> Path:
    return PIPELINE_ROOT / "dist" / "all-in-one" / "stage"


def default_output_dir() -> Path:
    return PIPELINE_ROOT / "dist" / "all-in-one" / "installer"


def installer_script() -> Path:
    return PIPELINE_ROOT / "installer" / "OntologyMachineAllInOne.iss"


def build_runtimes_script() -> Path:
    return TOOLS_DIR / "build-runtimes.py"


def all_in_one_config(module_root: Path) -> InstallerConfig:
    config = load_installer_config(module_root)
    module_name = module_root.name
    mutable_files = MODULE_MUTABLE_FILE_REPLACEMENTS.get(module_name, config.mutable_files)
    return replace(
        config,
        mutable_dirs=merge_unique(config.mutable_dirs, MODULE_MUTABLE_DIR_OVERRIDES.get(module_name, ())),
        mutable_files=merge_unique(mutable_files, MODULE_MUTABLE_FILE_OVERRIDES.get(module_name, ())),
    )


def merge_unique(base: tuple[str, ...], extra: tuple[str, ...]) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for item in (*base, *extra):
        normalized = item.strip().replace("/", "\\")
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            values.append(normalized)
    return tuple(values)
