"""Path-stable surface for semantic release loading and materialization."""
from __future__ import annotations

from .adapter import (
    assert_default_release_write_allowed,
    load_active_release,
    load_published_release,
    load_release_from_path,
    stage_published_release,
    write_release_analysis,
)
from .domain import materialize_projection
from .merge_workflow import (
    COLLISION_ARCHIVE_EXISTING,
    COLLISION_OVERWRITE_EXISTING,
    SNAPSHOT_OVERRIDE_INTEGRITY_STATUS,
    SNAPSHOT_RISK_WARNING,
    build_merge_preflight,
    merge_corpus_databases,
    validate_collision_resolution,
    validate_snapshot_risk_confirmation,
)
from .policy import (
    analyze_release,
    build_release_fingerprint,
    installation_state_drift_reason,
    materialize_promotions,
    projection_metadata,
)
from .runtime_truth import (
    build_activation_preflight,
    ensure_mutation_runtime_release,
    inspect_runtime_release,
    validate_activation_confirmation,
)
from .repository import collect_semantic_status, inspect_release_application_compatibility
from .snapshots import build_snapshot_envelope, build_snapshot_id, read_active_snapshot, resolve_runtime_locale
from .shared_identity import resolve_master_taxonomy_release_id
from .types import CompatibilityReport, MaterializedSemantics, ProjectionMetadata, ReleaseAnalysis, ReleasePayload
from .validation import REQUIRED_RELEASE_KEYS, assert_release_can_be_applied, validate_payload_against_release
from .workflow import materialize_document_semantics

__all__ = [
    "CompatibilityReport",
    "MaterializedSemantics",
    "ProjectionMetadata",
    "REQUIRED_RELEASE_KEYS",
    "ReleaseAnalysis",
    "ReleasePayload",
    "analyze_release",
    "assert_default_release_write_allowed",
    "assert_release_can_be_applied",
    "build_release_fingerprint",
    "build_snapshot_envelope",
    "build_snapshot_id",
    "build_activation_preflight",
    "collect_semantic_status",
    "build_merge_preflight",
    "ensure_mutation_runtime_release",
    "inspect_release_application_compatibility",
    "inspect_runtime_release",
    "installation_state_drift_reason",
    "load_active_release",
    "load_published_release",
    "load_release_from_path",
    "materialize_document_semantics",
    "materialize_promotions",
    "materialize_projection",
    "merge_corpus_databases",
    "projection_metadata",
    "read_active_snapshot",
    "resolve_runtime_locale",
    "resolve_master_taxonomy_release_id",
    "stage_published_release",
    "COLLISION_ARCHIVE_EXISTING",
    "COLLISION_OVERWRITE_EXISTING",
    "SNAPSHOT_OVERRIDE_INTEGRITY_STATUS",
    "SNAPSHOT_RISK_WARNING",
    "validate_collision_resolution",
    "validate_activation_confirmation",
    "validate_snapshot_risk_confirmation",
    "validate_payload_against_release",
    "write_release_analysis",
]
