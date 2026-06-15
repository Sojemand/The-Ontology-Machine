"""Named contracts for semantic release workflow stages."""
from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class TaxonomyAnalysisSummary(TypedDict):
    taxonomy_id: str | None
    taxonomy_version: str | None
    projection_count: int
    field_code_count: int
    row_type_count: int
    cell_code_count: int
    field_binding_coverage: float


class TaxonomySuitability(TypedDict):
    entity_model_ready: bool
    projection_growth_ready: bool
    on_prem_versioning_ready: bool
    deterministic_materialization_ready: bool


class TaxonomyAnalysisReport(TypedDict):
    summary: TaxonomyAnalysisSummary
    suitability: TaxonomySuitability
    issues: list[str]
    warnings: list[str]
    recommendations: list[str]


class SemanticReleaseRecipe(TypedDict):
    release_id: str
    release_version: str
    projection_ids: list[str]
    materialization_version: str


class SemanticReleasePayload(TypedDict):
    schema_version: str
    release_id: str
    release_version: str
    master_taxonomy_id: Any
    master_taxonomy_version: Any
    master_taxonomy_release_id: str
    runtime_locale: str
    projection_ids: list[str]
    materialization_version: str
    created_at: str
    fingerprint: str
    master_taxonomy: dict[str, Any]
    projections: list[dict[str, Any]]
    analysis: TaxonomyAnalysisReport
    projection_catalog: NotRequired[dict[str, Any]]
    runtime_semantic_assets: NotRequired[dict[str, Any]]
