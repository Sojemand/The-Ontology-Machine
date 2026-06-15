from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
NORMALIZER_ROOT = PIPELINE_ROOT / "04 - Normalizer"

if str(NORMALIZER_ROOT) not in sys.path:
    sys.path.insert(0, str(NORMALIZER_ROOT))

from normalizer_vision.runtime_semantic_assets import build_runtime_semantic_assets
from normalizer_vision.semantic_release import build_semantic_release


def build_locale_runtime_artifacts(tmp_path: Path, *, runtime_locale: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    if runtime_locale != "en":
        raise ValueError("Only the canonical en control locale is supported.")
    project_root = _copy_normalizer_project(tmp_path / f"normalizer_project_{runtime_locale}")
    release = build_semantic_release(project_root, target_locale=None)
    runtime_assets = build_runtime_semantic_assets(release).to_dict()
    return project_root, release, runtime_assets


def _copy_normalizer_project(root: Path) -> Path:
    if root.exists():
        shutil.rmtree(root)
    (root / "config").mkdir(parents=True)
    (root / "output").mkdir(parents=True)
    (root / "state").mkdir(parents=True)
    shutil.copy(NORMALIZER_ROOT / "module-manifest.json", root / "module-manifest.json")
    shutil.copy(NORMALIZER_ROOT / "config" / "config.yaml", root / "config" / "config.yaml")
    for taxonomy_path in (NORMALIZER_ROOT / "config").glob("normalizer_taxonomy.*.json"):
        shutil.copy(taxonomy_path, root / "config" / taxonomy_path.name)
    shutil.copytree(
        NORMALIZER_ROOT / "config" / "taxonomy_sources",
        root / "config" / "taxonomy_sources",
    )
    shutil.copy(NORMALIZER_ROOT / "config" / "prompt_bundle.json", root / "config" / "prompt_bundle.json")
    shutil.copy(NORMALIZER_ROOT / "config" / "prompt_overrides.json", root / "config" / "prompt_overrides.json")
    shutil.copy(NORMALIZER_ROOT / "config" / "semantic_release.recipe.json", root / "config" / "semantic_release.recipe.json")
    return root
