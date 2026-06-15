"""Path-stable surface for semantic release publishing and taxonomy analysis."""
from __future__ import annotations

from .adapter import load_local_projection_payloads, save_semantic_release
from .policy import analyze_taxonomy_shape, budget_semantic_release_file_name, semantic_release_file_name
from .recipe import default_publish_output_path, default_recipe, load_recipe, save_recipe, validate_recipe_payload
from .types import (
    SemanticReleasePayload,
    SemanticReleaseRecipe,
    TaxonomyAnalysisReport,
    TaxonomyAnalysisSummary,
    TaxonomySuitability,
)
from .workflow import (
    build_semantic_release,
    build_semantic_release_core_from_compiled,
    build_semantic_release_from_source_package,
    publish_semantic_release,
)

__all__ = [
    "SemanticReleasePayload",
    "SemanticReleaseRecipe",
    "TaxonomyAnalysisReport",
    "TaxonomyAnalysisSummary",
    "TaxonomySuitability",
    "analyze_taxonomy_shape",
    "budget_semantic_release_file_name",
    "build_semantic_release",
    "build_semantic_release_core_from_compiled",
    "build_semantic_release_from_source_package",
    "default_publish_output_path",
    "default_recipe",
    "load_local_projection_payloads",
    "load_recipe",
    "publish_semantic_release",
    "save_recipe",
    "save_semantic_release",
    "semantic_release_file_name",
    "validate_recipe_payload",
]
