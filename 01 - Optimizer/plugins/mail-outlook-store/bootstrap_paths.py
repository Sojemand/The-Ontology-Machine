from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BOOTSTRAP_VERSION = "1.1.0"
EMBEDDED_PYTHON_VERSION = "3.9.13"
EMBEDDED_PYTHON_FILENAME = f"python-{EMBEDDED_PYTHON_VERSION}-embed-amd64.zip"
EMBEDDED_PYTHON_URL = f"https://www.python.org/ftp/python/{EMBEDDED_PYTHON_VERSION}/{EMBEDDED_PYTHON_FILENAME}"
VENDORED_WHEELS = (
    {"project": "libpff-python", "version": "20211114", "filename": "libpff_python-20211114-cp39-cp39-win_amd64.whl"},
    {"project": "pywin32", "version": "311", "filename": "pywin32-311-cp39-cp39-win_amd64.whl"},
)


@dataclass(frozen=True)
class PluginPaths:
    plugin_dir: Path
    runtime_root: Path
    runtime_dir: Path
    wheelhouse_dir: Path
    vendor_dir: Path
    install_state_path: Path
    requirements_path: Path


def resolve_paths(plugin_dir: Path) -> PluginPaths:
    runtime_root = plugin_dir / "runtime"
    return PluginPaths(
        plugin_dir=plugin_dir,
        runtime_root=runtime_root,
        runtime_dir=runtime_root / "python",
        wheelhouse_dir=runtime_root / "wheelhouse",
        vendor_dir=runtime_root / "vendor",
        install_state_path=runtime_root / "install_state.json",
        requirements_path=plugin_dir / "requirements.txt",
    )
