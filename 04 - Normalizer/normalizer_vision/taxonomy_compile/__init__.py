"""Path-stable source-package compiler for release-ready taxonomy payloads."""
from __future__ import annotations

from .policy import compile_source_package, source_recipe_defaults
from .types import CompiledTaxonomyAssets
from .workflow import ensure_compiled_taxonomy_assets, require_compiled_taxonomy_assets

__all__ = [
    "CompiledTaxonomyAssets",
    "compile_source_package",
    "ensure_compiled_taxonomy_assets",
    "require_compiled_taxonomy_assets",
    "source_recipe_defaults",
]
