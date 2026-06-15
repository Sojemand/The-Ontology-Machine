"""Pure source-package compile workflow without on-disk flat artifacts."""
from __future__ import annotations

from pathlib import Path

from ..taxonomy_sources import has_source_package, load_source_package
from .policy import compile_source_package
from .types import CompiledTaxonomyAssets


def ensure_compiled_taxonomy_assets(
    project_root: Path,
    *,
    target_locale: str | None = None,
) -> CompiledTaxonomyAssets | None:
    if not has_source_package(project_root):
        return None
    return compile_source_package(
        load_source_package(project_root),
        target_locale=target_locale,
    )


def require_compiled_taxonomy_assets(project_root: Path) -> CompiledTaxonomyAssets | None:
    return ensure_compiled_taxonomy_assets(project_root)
