from __future__ import annotations

from .types import (
    BackfillSqlFromMergeArtifactsCommand,
    CleanupPipelineBatchMaterializationCommand,
    ExtractSampleFilesForReingestCommand,
    InspectLatestPipelineBatchCommand,
    MultiSourceMergeDatabasesCommand,
    MultiSourceMergePreflightCommand,
    ReadDatabaseAnalysisEvidenceCommand,
    ReingestPipelineBatchCommand,
    RestorePipelineBatchOriginalsCommand,
    ValidateArtifactTreeCommand,
    WriteMergeReconciliationManifestCommand,
)
from .validation_common import reject_unknown_keys
from .validation_keys import _DATABASE_ANALYSIS_KEYS, _MERGE_PHASE19_KEYS, _PIPELINE_BATCH_KEYS, _VALIDATE_ARTIFACT_TREE_KEYS
from .validation_owner_envelope import _require_phase19_owner_envelope


def parse_validate_artifact_tree_command(payload: dict) -> ValidateArtifactTreeCommand:
    reject_unknown_keys(payload, _VALIDATE_ARTIFACT_TREE_KEYS)
    _require_phase19_owner_envelope(payload, "validate_artifact_tree")
    return ValidateArtifactTreeCommand(payload=dict(payload))


def parse_read_database_analysis_evidence_command(payload: dict) -> ReadDatabaseAnalysisEvidenceCommand:
    reject_unknown_keys(payload, _DATABASE_ANALYSIS_KEYS)
    _require_phase19_owner_envelope(payload, "read_database_analysis_evidence")
    return ReadDatabaseAnalysisEvidenceCommand(payload=dict(payload))


def parse_inspect_latest_pipeline_batch_command(payload: dict) -> InspectLatestPipelineBatchCommand:
    reject_unknown_keys(payload, _PIPELINE_BATCH_KEYS)
    _require_phase19_owner_envelope(payload, "inspect_latest_pipeline_batch")
    return InspectLatestPipelineBatchCommand(payload=dict(payload))


def parse_extract_sample_files_for_reingest_command(payload: dict) -> ExtractSampleFilesForReingestCommand:
    reject_unknown_keys(payload, _PIPELINE_BATCH_KEYS)
    _require_phase19_owner_envelope(payload, "extract_sample_files_for_reingest")
    return ExtractSampleFilesForReingestCommand(payload=dict(payload))


def parse_restore_pipeline_batch_originals_command(payload: dict) -> RestorePipelineBatchOriginalsCommand:
    reject_unknown_keys(payload, _PIPELINE_BATCH_KEYS)
    _require_phase19_owner_envelope(payload, "restore_pipeline_batch_originals")
    return RestorePipelineBatchOriginalsCommand(payload=dict(payload))


def parse_cleanup_pipeline_batch_materialization_command(payload: dict) -> CleanupPipelineBatchMaterializationCommand:
    reject_unknown_keys(payload, _PIPELINE_BATCH_KEYS)
    _require_phase19_owner_envelope(payload, "cleanup_pipeline_batch_materialization")
    return CleanupPipelineBatchMaterializationCommand(payload=dict(payload))


def parse_reingest_pipeline_batch_command(payload: dict) -> ReingestPipelineBatchCommand:
    reject_unknown_keys(payload, _PIPELINE_BATCH_KEYS)
    _require_phase19_owner_envelope(payload, "reingest_pipeline_batch")
    return ReingestPipelineBatchCommand(payload=dict(payload))


def parse_multi_source_merge_preflight_command(payload: dict) -> MultiSourceMergePreflightCommand:
    reject_unknown_keys(payload, _MERGE_PHASE19_KEYS)
    _require_phase19_owner_envelope(payload, "multi_source_merge_preflight")
    return MultiSourceMergePreflightCommand(payload=dict(payload))


def parse_multi_source_merge_databases_command(payload: dict) -> MultiSourceMergeDatabasesCommand:
    reject_unknown_keys(payload, _MERGE_PHASE19_KEYS)
    _require_phase19_owner_envelope(payload, "multi_source_merge_databases")
    return MultiSourceMergeDatabasesCommand(payload=dict(payload))


def parse_write_merge_reconciliation_manifest_command(payload: dict) -> WriteMergeReconciliationManifestCommand:
    reject_unknown_keys(payload, _MERGE_PHASE19_KEYS)
    _require_phase19_owner_envelope(payload, "write_merge_reconciliation_manifest")
    return WriteMergeReconciliationManifestCommand(payload=dict(payload))


def parse_backfill_sql_from_merge_artifacts_command(payload: dict) -> BackfillSqlFromMergeArtifactsCommand:
    reject_unknown_keys(payload, _MERGE_PHASE19_KEYS)
    _require_phase19_owner_envelope(payload, "backfill_sql_from_merge_artifacts")
    return BackfillSqlFromMergeArtifactsCommand(payload=dict(payload))
