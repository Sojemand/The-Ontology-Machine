from __future__ import annotations

from types import MappingProxyType

from semantic_control_kernel.types.enums import RecoveryStateClass


RECOVERY_BY_BLOCKER = MappingProxyType(
    {
        "active_run_lock_conflict": RecoveryStateClass.STALE_LOCK.value,
        "expired_lock_requires_recovery": RecoveryStateClass.STALE_LOCK.value,
        "invalid_target_path": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "target_conflict": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "target_identity_changed": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "database_missing": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "database_empty": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "database_not_empty": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "database_emptiness_unknown": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "release_fingerprint_mismatch": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "semantic_release_preservation_failed": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "additive_only_lock_missing": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "non_additive_selected_for_filled_database": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "missing_artifact_tree": RecoveryStateClass.BROKEN_DATABASE_ARTIFACT_BINDING.value,
        "binding_missing": RecoveryStateClass.BROKEN_DATABASE_ARTIFACT_BINDING.value,
        "binding_conflict": RecoveryStateClass.BROKEN_DATABASE_ARTIFACT_BINDING.value,
        "release_missing": RecoveryStateClass.SEMANTIC_RELEASE_INCOMPLETE_STAGED.value,
        "release_incomplete": RecoveryStateClass.SEMANTIC_RELEASE_INCOMPLETE_STAGED.value,
        "release_not_written": RecoveryStateClass.SEMANTIC_RELEASE_INCOMPLETE_STAGED.value,
        "attach_pointer_missing": RecoveryStateClass.SEMANTIC_RELEASE_INCOMPLETE_STAGED.value,
        "projection_taxonomy_invalid": RecoveryStateClass.SEMANTIC_RELEASE_INCOMPLETE_STAGED.value,
        "source_manifest_stale": RecoveryStateClass.PARTIAL_PIPELINE_RUN.value,
        "records_not_isolated": RecoveryStateClass.PARTIAL_PIPELINE_RUN.value,
        "materialization_provenance_missing": RecoveryStateClass.PARTIAL_PIPELINE_RUN.value,
        "partial_pipeline_run": RecoveryStateClass.PARTIAL_PIPELINE_RUN.value,
        "merge_mixed_emptiness": RecoveryStateClass.UNRESOLVED_MERGE_COLLISION.value,
        "merge_collision_unresolved": RecoveryStateClass.UNRESOLVED_MERGE_COLLISION.value,
        "merge_policy_missing": RecoveryStateClass.UNRESOLVED_MERGE_COLLISION.value,
        "source_state_unknown": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "input_missing": RecoveryStateClass.MISSING_MANIFEST_OR_ORIGINALS.value,
        "input_collision_unresolved": RecoveryStateClass.MISSING_MANIFEST_OR_ORIGINALS.value,
        "sample_manifest_missing": RecoveryStateClass.MISSING_MANIFEST_OR_ORIGINALS.value,
        "originals_missing": RecoveryStateClass.MISSING_MANIFEST_OR_ORIGINALS.value,
        "source_cleanup_unjournaled": RecoveryStateClass.MISSING_MANIFEST_OR_ORIGINALS.value,
        "batch_manifest_missing": RecoveryStateClass.MISSING_MANIFEST_OR_ORIGINALS.value,
        "update_state_invalid": RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value,
        "confirmation_missing": RecoveryStateClass.EXPIRED_PENDING_INTERACTION.value,
        "confirmation_stale": RecoveryStateClass.EXPIRED_PENDING_INTERACTION.value,
        "missing_required_state": RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value,
        "unknown_state": RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value,
        "embedding_unavailable": RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value,
        "deprecated_function": RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value,
        "pipeline_capability_missing": RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value,
        "owner_evidence_conflict": RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value,
    }
)

BLOCKER_CODES: tuple[str, ...] = tuple(RECOVERY_BY_BLOCKER)


def recovery_for_blocker(blocker_code: str) -> str:
    try:
        return RECOVERY_BY_BLOCKER[blocker_code]
    except KeyError as exc:
        raise ValueError(f"Unknown blocker code: {blocker_code}") from exc


def validate_recovery_mapping(blocker_codes: tuple[str, ...] = BLOCKER_CODES) -> None:
    missing = sorted(set(blocker_codes) - set(RECOVERY_BY_BLOCKER))
    if missing:
        raise ValueError(f"Blocker code(s) missing recovery mapping: {', '.join(missing)}")
    recovery_values = set(RecoveryStateClass.values())
    unknown_recoveries = sorted(set(RECOVERY_BY_BLOCKER.values()) - recovery_values)
    if unknown_recoveries:
        raise ValueError(f"Unknown recovery state class(es): {', '.join(unknown_recoveries)}")
