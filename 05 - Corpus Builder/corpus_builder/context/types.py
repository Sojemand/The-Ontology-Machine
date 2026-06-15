"""Named path carrier for the Corpus Builder runtime context contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ContextPaths:
    module_root: Path
    config_dir: Path
    mutable_runtime_dir: Path
    bundled_runtime_dir: Path
    state_dir: Path
    output_dir: Path
    config_path: Path
    semantic_release_state_path: Path
    semantic_release_report_path: Path
