from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from semantic_control_kernel.types.enums import DialogType, InteractionKind


RESPONSE_VALUE_FIELDS: tuple[str, ...] = (
    "path_value",
    "text_value",
    "choice_id",
    "selected_database_paths",
    "confirmation_decision",
    "recovery_id",
)

CANCELLATION_REASON_VALUES: tuple[str, ...] = (
    "user_closed_dialog",
    "user_cancelled",
    "timeout",
    "superseded_workflow_run",
    "target_identity_changed",
    "host_surface_unavailable",
)


@dataclass(frozen=True)
class ExpirationPolicyDefinition:
    policy_id: str
    ttl_seconds: int | None
    recovery_state: str | None


EXPIRATION_POLICIES: dict[str, ExpirationPolicyDefinition] = {
    "selection_short": ExpirationPolicyDefinition("selection_short", 1800, "expired_pending_interaction"),
    "selection_long": ExpirationPolicyDefinition("selection_long", 7200, "expired_pending_interaction"),
    "confirmation_destructive": ExpirationPolicyDefinition("confirmation_destructive", 900, "expired_pending_interaction"),
    "confirmation_long_running": ExpirationPolicyDefinition("confirmation_long_running", 1800, "expired_pending_interaction"),
    "notice_no_response": ExpirationPolicyDefinition("notice_no_response", None, None),
    "recovery_event_scoped": ExpirationPolicyDefinition("recovery_event_scoped", 1800, "expired_pending_interaction"),
}


@dataclass(frozen=True)
class UserInteractionMapping:
    interaction_function: str
    interaction_kind: str
    dialog_type: str
    response_value_fields: tuple[str, ...]
    required_target_identity_fields: tuple[str, ...]
    optional_target_identity_fields: tuple[str, ...]
    expiration_policy_id: str

    @property
    def response_shape(self) -> str:
        return self.response_value_fields[0] if len(self.response_value_fields) == 1 else "_or_".join(self.response_value_fields)

    @property
    def target_identity_fields(self) -> tuple[str, ...]:
        return self.required_target_identity_fields + self.optional_target_identity_fields


_USER_INTERACTION_ROWS: tuple[tuple[str, str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...], str], ...] = (
    ("choose_artifact_root_folder", InteractionKind.SELECTION.value, DialogType.FOLDER_PICKER.value, ("path_value",), ("artifact_root_path_hash",), ("workflow_run_id",), "selection_short"),
    ("name_artifact_root_folder", InteractionKind.INPUT.value, DialogType.FOLDER_CREATE_PICKER.value, ("path_value", "text_value"), ("artifact_root_path_hash",), ("parent_path_hash",), "selection_short"),
    ("name_database", InteractionKind.INPUT.value, DialogType.TEXT_INPUT.value, ("text_value",), ("artifact_root_path_hash",), ("database_path_hash",), "selection_short"),
    ("select_sample_files", InteractionKind.CONFIRMATION.value, DialogType.INPUT_PRESENCE_CONFIRMATION.value, ("confirmation_decision",), ("artifact_root_path_hash", "input_path_hash", "database_path_hash"), (), "confirmation_long_running"),
    ("use_current_active_database", InteractionKind.SELECTION.value, DialogType.ACTIVE_DATABASE_CHOICE.value, ("choice_id",), ("database_path_hash", "database_id", "artifact_root_path_hash"), (), "selection_short"),
    ("use_custom_database_path", InteractionKind.SELECTION.value, DialogType.DATABASE_PATH_PICKER.value, ("path_value",), ("database_path_hash",), ("database_id", "artifact_root_path_hash"), "selection_short"),
    ("choose_merge_database_count", InteractionKind.INPUT.value, DialogType.TEXT_INPUT.value, ("text_value",), ("source_database_set_hash",), ("database_path_hash",), "selection_short"),
    ("choose_databases_to_merge", InteractionKind.SELECTION.value, DialogType.DATABASE_LIST_PICKER.value, ("selected_database_paths",), ("source_database_set_hash", "database_path_hash"), ("database_id",), "selection_long"),
    ("choose_new_artifact_root_folder", InteractionKind.SELECTION.value, DialogType.FOLDER_CREATE_PICKER.value, ("path_value",), ("artifact_root_path_hash", "target_hash"), (), "selection_short"),
    ("choose_merge_projection_mode", InteractionKind.SELECTION.value, DialogType.UPDATE_MODE_CHOICE.value, ("choice_id",), ("source_database_set_hash", "target_hash"), (), "selection_short"),
    ("user_confirmation", InteractionKind.CONFIRMATION.value, DialogType.GENERIC_CONFIRMATION.value, ("confirmation_decision",), (), (), "confirmation_destructive"),
)

USER_INTERACTION_MAPPINGS: dict[str, UserInteractionMapping] = {
    row[0]: UserInteractionMapping(*row) for row in _USER_INTERACTION_ROWS
}


@dataclass(frozen=True)
class RecoveryDialogMapping:
    recovery_dialog_type: str
    used_for: tuple[str, ...]
    response_value_fields: tuple[str, ...]
    allowed_owner: tuple[str, ...]


_RECOVERY_DIALOG_ROWS: tuple[tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]], ...] = (
    ("path_reselection_dialog", ("invalid_target_path", "target_identity_changed", "moved_folder", "missing_database_path", "missing_artifact_tree_path"), ("path_value", "cancellation_reason"), ("kernel_dialog",)),
    ("missing_input_dialog", ("input_missing", "sample_manifest_missing", "originals_missing", "batch_manifest_missing"), ("confirmation_decision",), ("kernel_dialog", "user_filesystem_action")),
    ("overwrite_decision_dialog", ("existing_target_database", "existing_target_folder", "rebuild_overwrite"), ("confirmation_decision", "path_value"), ("kernel_dialog",)),
    ("merge_reconciliation_dialog", ("unresolved_merge_collision", "merge_policy_missing", "semantic_collision_unresolved"), ("choice_id",), ("kernel_dialog",)),
    ("stale_lock_dialog", ("stale_lock", "expired_lock_requires_recovery", "active_run_lock_conflict"), ("choice_id",), ("kernel_dialog",)),
    ("rebind_database_artifact_tree_dialog", ("broken_database_artifact_binding", "binding_missing", "binding_conflict"), ("path_value",), ("kernel_dialog",)),
    ("discard_or_archive_staged_work_dialog", ("staged_work_abandonment", "semantic_release_incomplete_staged", "abandoned_merge_target"), ("confirmation_decision",), ("kernel_dialog",)),
    ("partial_pipeline_run_recovery_dialog", ("partial_pipeline_run",), ("recovery_id",), ("kernel_dialog",)),
    ("support_bundle_dialog", ("support_only_unrecoverable", "final_errors", "unsafe_recovery_evidence"), ("confirmation_decision",), ("support_surface",)),
)

RECOVERY_DIALOG_MAPPINGS: dict[str, RecoveryDialogMapping] = {
    row[0]: RecoveryDialogMapping(*row) for row in _RECOVERY_DIALOG_ROWS
}


def build_expiration_policy(policy_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    definition = EXPIRATION_POLICIES[policy_id]
    payload: dict[str, Any] = {"policy_id": definition.policy_id}
    if definition.ttl_seconds is not None:
        created = now or datetime.now(timezone.utc)
        expires = created + timedelta(seconds=definition.ttl_seconds)
        payload["ttl_seconds"] = definition.ttl_seconds
        payload["expires_at"] = expires.isoformat().replace("+00:00", "Z")
    if definition.recovery_state is not None:
        payload["recovery_state"] = definition.recovery_state
    return payload
