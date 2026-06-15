from __future__ import annotations

import json

from pathlib import Path

from normalizer_vision.models import load_config

from normalizer_vision.normalizer import DocumentNormalizer

from normalizer_vision.projection_routing import resolve_projection

from normalizer_vision.assets import load_local_profile

from normalizer_vision.semantic_release import build_semantic_release

from tests.fixtures.normalizer_cases import apply_operations_raw_signals, operations_output

def _normalized_output_path(project_root: Path, structured_path: Path) -> Path:
    return project_root / "output" / structured_path.name.replace(".structured.json", ".structured.normalized.json")

__all__ = [name for name in globals() if not name.startswith("__")]
