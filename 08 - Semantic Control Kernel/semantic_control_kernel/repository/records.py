from __future__ import annotations

from semantic_control_kernel.repository.record_base import RepositoryRecord


class StateRootManifestRecord(RepositoryRecord):
    SCHEMA_VERSION = "repository.state_root_manifest.v1"
    REQUIRED_FIELDS = (
        "schema_version",
        "created_at",
        "module_key",
        "state_layout_version",
        "state_root_path",
    )


class WorkflowRunRecord(RepositoryRecord):
    SCHEMA_VERSION = "repository.workflow_run_record.v1"
    REQUIRED_FIELDS = (
        "schema_version",
        "workflow_run_id",
        "workflow_tool",
        "target_identity",
        "status",
        "started_by",
        "created_at",
        "updated_at",
    )
    OPTIONAL_FIELDS = (
        "resume_state_ref",
        "operation_receipt_id",
        "support_bundle_ref",
        "recovery_receipt_id",
    )
    ENUM_FIELDS = {"status": ("running", "waiting", "completed", "failed", "cancelled")}


class PendingConfirmationRecord(RepositoryRecord):
    SCHEMA_VERSION = "repository.pending_confirmation_record.v1"
    REQUIRED_FIELDS = (
        "schema_version",
        "confirmation_request",
        "status",
        "workflow_run_id",
        "target_identity",
        "state_snapshot_identity",
        "created_at",
        "updated_at",
    )
    OPTIONAL_FIELDS = ("expiration_reason", "confirmation_receipt_id", "cancellation_reason")
    ENUM_FIELDS = {"status": ("pending", "consumed", "expired", "cancelled")}


class PendingInteractionRecord(RepositoryRecord):
    SCHEMA_VERSION = "repository.pending_interaction_record.v1"
    REQUIRED_FIELDS = (
        "schema_version",
        "interaction_request",
        "status",
        "workflow_run_id",
        "target_identity",
        "state_snapshot_identity",
        "created_at",
        "updated_at",
    )
    OPTIONAL_FIELDS = (
        "interaction_response_id",
        "interaction_response",
        "reason",
        "superseding_workflow_run_id",
        "stale_response_refs",
    )
    ENUM_FIELDS = {
        "status": (
            "pending",
            "submitted",
            "cancelled",
            "closed",
            "expired",
            "superseded",
            "rejected_stale",
        )
    }


class ReceiptIndexRecord(RepositoryRecord):
    SCHEMA_VERSION = "repository.receipt_index.v1"
    REQUIRED_FIELDS = (
        "schema_version",
        "index_kind",
        "index_key",
        "receipt_refs",
        "rebuilt_at",
    )


class MirrorToolAvailability(RepositoryRecord):
    SCHEMA_VERSION = "repository.mirror_tool_availability.v1"
    REQUIRED_FIELDS = (
        "schema_version",
        "mirror_event_id",
        "allowed_agent_tools",
        "status",
        "created_at",
        "expires_at",
        "updated_at",
    )
    OPTIONAL_FIELDS = ("reason",)
    ENUM_FIELDS = {"status": ("active", "expired", "consumed", "superseded")}


class ActiveArtifactTreeRef(RepositoryRecord):
    SCHEMA_VERSION = "repository.active_artifact_tree_ref.v1"
    REQUIRED_FIELDS = (
        "schema_version",
        "artifact_root_path",
        "artifact_root_path_hash",
        "folder_contract_version",
        "canonical_paths",
        "target_identity",
        "validation_receipt_id",
        "validated_at",
        "status",
    )
    OPTIONAL_FIELDS = ("evidence_refs", "stale_reason", "operation_receipt_id")
    ENUM_FIELDS = {"status": ("active", "stale", "superseded")}


class SupportBundleIndexRecord(RepositoryRecord):
    SCHEMA_VERSION = "repository.support_bundle_index.v1"
    REQUIRED_FIELDS = ("schema_version", "support_bundle_refs", "updated_at")


class ResetManifestRecord(RepositoryRecord):
    SCHEMA_VERSION = "repository.reset_manifest.v1"
    REQUIRED_FIELDS = (
        "schema_version",
        "reset_id",
        "created_at",
        "archived_paths",
        "preserved_paths",
        "reason",
    )


class QuarantineReasonRecord(RepositoryRecord):
    SCHEMA_VERSION = "repository.quarantine_reason.v1"
    REQUIRED_FIELDS = (
        "schema_version",
        "quarantine_id",
        "original_path",
        "quarantined_path",
        "reason",
        "exception_class",
        "created_at",
    )
