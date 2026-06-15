"""Bootstrap workflow for module root and state validation."""

from __future__ import annotations

from pathlib import Path

from ..repository import ensure_state_layout
from .types import StartupContext
from .validation import require_directory, require_file

EDIT_SUITE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = EDIT_SUITE_ROOT.parent
STATE_ROOT = EDIT_SUITE_ROOT / "state"


def module_root(root: str | Path | None = None) -> Path:
    return Path(root or EDIT_SUITE_ROOT).resolve()


def pipeline_root(root: str | Path | None = None) -> Path:
    return module_root(root).parent.resolve()


def ensure_startup_prerequisites(root: str | Path | None = None) -> StartupContext:
    current_root = module_root(root)
    require_directory(current_root, label="Modulroot")
    require_file(current_root / "module-manifest.json", label="module-manifest.json")
    current_pipeline_root = pipeline_root(current_root)
    require_directory(current_pipeline_root, label="Pipeline-Root")
    state_root = ensure_state_layout(current_root / "state")
    return StartupContext(
        module_root=current_root,
        pipeline_root=current_pipeline_root,
        state_root=state_root.resolve(),
    )
