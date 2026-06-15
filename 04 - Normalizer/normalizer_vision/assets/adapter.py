"""Boundary stage for stable local asset paths."""
from __future__ import annotations

from pathlib import Path

PROMPT_BUNDLE_RELATIVE_PATH = Path("config/prompt_bundle.json")
PROMPT_OVERRIDES_RELATIVE_PATH = Path("config/prompt_overrides.json")
SEMANTIC_RELEASE_RECIPE_RELATIVE_PATH = Path("config/semantic_release.recipe.json")


def prompt_overrides_path(project_root: Path) -> Path:
    return project_root / PROMPT_OVERRIDES_RELATIVE_PATH


def prompt_bundle_path(project_root: Path) -> Path:
    return project_root / PROMPT_BUNDLE_RELATIVE_PATH


def semantic_release_recipe_path(project_root: Path) -> Path:
    return project_root / SEMANTIC_RELEASE_RECIPE_RELATIVE_PATH
