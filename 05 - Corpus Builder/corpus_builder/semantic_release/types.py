"""Named contracts for semantic release stages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict


class ReleasePayload(TypedDict):
    release_id: str
    release_version: str
    master_taxonomy_id: Any
    master_taxonomy_version: Any
    master_taxonomy_release_id: NotRequired[str]
    runtime_locale: NotRequired[str]
    projection_catalog: NotRequired[dict[str, Any]]
    runtime_semantic_assets: NotRequired[dict[str, Any]]
    active_snapshot: NotRequired[dict[str, Any]]
    projection_ids: list[str]
    materialization_version: str
    fingerprint: str
    master_taxonomy: dict[str, Any]
    projections: list[dict[str, Any]]


class ReleaseAnalysis(TypedDict):
    release_id: Any
    release_version: Any
    projection_count: int
    issues: list[str]
    warnings: list[str]
    generated_at: str


class ProjectionMetadata(TypedDict):
    projection_id: str
    projection_family: str
    master_taxonomy_id: str
    master_taxonomy_version: str
    projection_version: str
    projection_fingerprint: str
    materialization_profile_id: str


class CompatibilityReport(TypedDict):
    missing_projection_ids: list[str]
    incompatible_projection_ids: list[str]
    foreign_master_ids: list[str]


class SemanticStatusReport(TypedDict):
    total_documents: int
    stale_documents: int
    active_snapshot_id: Any
    active_release_id: Any
    active_release_version: Any
    active_release_fingerprint: Any
    active_master_taxonomy_release_id: Any
    active_runtime_locale: Any
    integrity_status: Any
    materialization_version: Any
    runtime_truth_source: str
    active_release_state_matches_installation_state: bool | None
    installation_state_drift_reason: str | None


class ProcessingState(TypedDict):
    document_id: str
    schema_version: str
    materialization_version: str
    materialized_snapshot_id: str | None
    projection_id: str
    projection_fingerprint: str
    materialization_state: str
    stale_reason: str | None
    source_mode: str
    last_materialized_at: str


class ActiveSnapshotEnvelope(TypedDict):
    snapshot_id: str
    release: dict[str, Any]
    projection_catalog: dict[str, Any]
    runtime_semantic_assets: dict[str, Any]
    master_taxonomy_release_id: str
    runtime_locale: str | None
    release_path: str


class SlotCandidate(TypedDict):
    slot: str
    display_value: Any
    normalized_value: str | None
    compact_value: str | None
    strategy: str
    confidence: float
    ambiguity_group: str
    is_projection_backed: int
    candidate_layer: str
    candidate_origin: str
    origin_path: str
    origin_kind: str
    evidence_paths: list[str]
    projection_id: str


class DocumentPromotion(TypedDict):
    slot: str
    slot_label: str | None
    value_type: str
    query_role: str | None
    display_value: str
    normalized_value: str | None
    compact_value: str | None
    numeric_value: float | None
    date_value: str | None
    value_json: str | None
    ordinal: int
    confidence: float
    source_path: str
    source_refs: list[str]
    projection_id: str
    release_fingerprint: str
    materialization_version: str


class MaterializedSemantics(TypedDict):
    projection_id: str
    projection_fingerprint: str
    document_promotions: list[DocumentPromotion]
    slot_candidates: list[SlotCandidate]
    entities: list[dict[str, Any]]
    entity_attributes: list[dict[str, Any]]
    entity_relations: list[dict[str, Any]]
    processing_state: ProcessingState
    audits: list[dict[str, Any]]


@dataclass(frozen=True)
class MaterializationInputs:
    document_id: str
    payload: dict[str, Any]
    projection: dict[str, Any]
    projection_meta: ProjectionMetadata
    materialization_version: str
    release_fingerprint: str
    active_snapshot_id: str | None = None
