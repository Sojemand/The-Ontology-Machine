"""Shared constants for snapshot-first corpus merges."""

SNAPSHOT_RISK_CONFIRMATION_VERSION = "semantic_merge_snapshot_risk_confirmation_v1"
COLLISION_RESOLUTION_VERSION = "semantic_merge_collision_resolution_v1"
SNAPSHOT_RISK_WARNING = "Semantic Snapshot korrupt oder unvollstaendig. DB trotzdem mergen?"
COLLISION_ARCHIVE_EXISTING = "archive_existing_then_import"
COLLISION_OVERWRITE_EXISTING = "overwrite_existing"
SNAPSHOT_OVERRIDE_INTEGRITY_STATUS = "snapshot_override_confirmed"

ACTIVE_DOC_SQL = "SELECT COUNT(*) FROM documents WHERE is_archived = 0"
DOCUMENT_ID_TABLES = (
    "document_payloads",
    "embeddings",
    "load_history",
    "extracted_fields",
    "extracted_rows",
    "relations",
    "tags",
    "people",
    "organizations",
    "documents_fts_content",
    "document_page_images",
    "evidence_atoms",
    "slot_candidates",
    "document_processing_state",
    "document_entities",
    "entity_relations",
    "materialization_audit",
)


__all__ = [
    "ACTIVE_DOC_SQL",
    "COLLISION_ARCHIVE_EXISTING",
    "COLLISION_OVERWRITE_EXISTING",
    "COLLISION_RESOLUTION_VERSION",
    "DOCUMENT_ID_TABLES",
    "SNAPSHOT_OVERRIDE_INTEGRITY_STATUS",
    "SNAPSHOT_RISK_CONFIRMATION_VERSION",
    "SNAPSHOT_RISK_WARNING",
]
