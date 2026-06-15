from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_MODULE_DIRS = (
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
ORCHESTRATOR_MODULE_DIR = "00 - Orchestrator"
CLIENT_FRONTEND_MODULE_DIR = "Client Frontend"
RUNTIME_PYTHON_VERSION = (3, 11)
RUNTIME_PYTHON_BITS = 64
RUNTIME_PYTHON_HOME_ENV = "VISION_PIPELINE_PYTHON311_HOME"
ORCHESTRATOR_PYTHON_HOME_ENV = "VISION_ORCHESTRATOR_PYTHON311_HOME"
LIBREOFFICE_BUILD_HOME_ENV = "VISION_LIBREOFFICE_BUILD_HOME"
PIN_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*==\s*([^\s;]+)")
VALIDATION_IMPORT_MAP = {
    "beautifulsoup4": "bs4",
    "extract-msg": "extract_msg",
    "cffi": "cffi",
    "customtkinter": "customtkinter",
    "darkdetect": "darkdetect",
    "markdown": "markdown",
    "odfpy": "odf",
    "numpy": "numpy",
    "olefile": "olefile",
    "oletools": "oletools",
    "packaging": "packaging",
    "pdfminer-six": "pdfminer",
    "pdfplumber": "pdfplumber",
    "pillow": "PIL",
    "pymupdf": "fitz",
    "python-docx": "docx",
    "pyyaml": "yaml",
    "rtfde": "RTFDE",
    "striprtf": "striprtf",
}


@dataclass(frozen=True)
class ModuleBuildTarget:
    root: Path

    @property
    def runtime_dir(self) -> Path:
        return self.root / "runtime" / "python"

    @property
    def wheelhouse_dir(self) -> Path:
        return self.root / "runtime" / "wheelhouse"

    @property
    def requirements_path(self) -> Path:
        return self.root / "requirements.txt"

    @property
    def lockfile_path(self) -> Path:
        return self.root / "runtime" / "requirements.lock.txt"

    @property
    def libreoffice_dir(self) -> Path:
        return self.root / "runtime" / "libreoffice"

    @property
    def libreoffice_soffice(self) -> Path:
        return self.libreoffice_dir / "program" / "soffice.exe"

    @property
    def libreoffice_cli(self) -> Path:
        if sys.platform == "win32":
            candidate = self.libreoffice_dir / "program" / "soffice.com"
            if candidate.exists():
                return candidate
        return self.libreoffice_soffice

    @property
    def module_manifest_path(self) -> Path:
        return self.root / "module-manifest.json"

    @property
    def manifest_payload(self) -> dict[str, object] | None:
        if not self.module_manifest_path.exists():
            return None
        try:
            payload = json.loads(self.module_manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    @property
    def module_key(self) -> str | None:
        payload = self.manifest_payload
        value = str((payload or {}).get("module_key") or "").strip()
        return value or None

    @property
    def is_optimizer(self) -> bool:
        return self.module_key == "optimizer" or self.root.name == "01 - Optimizer"

    @property
    def plugin_bootstraps(self) -> tuple[Path, ...]:
        if not self.is_optimizer:
            return ()
        return tuple(
            path
            for path in (self.root / "plugins" / "mail-outlook-store" / "bootstrap.py",)
            if path.exists()
        )

    @property
    def is_orchestrator(self) -> bool:
        return self.root.name == ORCHESTRATOR_MODULE_DIR

    @property
    def bundles_libreoffice(self) -> bool:
        return self.is_optimizer

    @property
    def is_client_frontend(self) -> bool:
        return self.root.name == CLIENT_FRONTEND_MODULE_DIR

    @property
    def package_name(self) -> str | None:
        payload = self.manifest_payload
        launcher_value = str((payload or {}).get("launcher_module") or "").strip()
        if launcher_value:
            return launcher_value
        value = str((payload or {}).get("module_key") or "").strip()
        return value or None

    @property
    def runtime_manifest_hook(self) -> Path | None:
        candidate = self.root / "tools" / "build-runtime.py"
        return candidate if candidate.exists() else None


def normalize_dist_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def requirements_entries(requirements_path: Path) -> list[str]:
    if not requirements_path.exists():
        return []
    return [
        line
        for raw_line in requirements_path.read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip()) and not line.startswith("#")
    ]


def has_runtime_packages(requirements_path: Path) -> bool:
    return bool(requirements_entries(requirements_path))
