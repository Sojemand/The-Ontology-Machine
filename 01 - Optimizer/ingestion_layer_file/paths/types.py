"""Named path carriers for the Optimizer runtime layout."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PathLayout:
    module_root: Path
    app_home: Path
    config_dir: Path
    state_dir: Path
    output_dir: Path
    log_dir: Path
    plugins_dir: Path
    runtime_dir: Path
    libreoffice_dir: Path
    bundled_config_dir: Path
    default_config_path: Path

