from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.domain.recovery.tool_authorization import validate_recovery_option_binding
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.types.enums import RecoveryResultStatus


class StagedWorkArchiveService:
    def __init__(self, paths: StatePaths, recovery_store: RecoveryEventStore) -> None:
        self.paths = paths
        self.recovery_store = recovery_store
        self._json = AtomicJsonStore(paths, "staged_work_archive")

    def archive_or_discard(
        self,
        recovery_event: Mapping[str, Any],
        recovery_id: str,
        staged_work_ref: str,
        *,
        original_refs: Sequence[Mapping[str, Any]] = (),
        destructive: bool = False,
        confirmation_ref: Mapping[str, Any] | None = None,
        scope_is_explicit: bool = False,
        targets_active_production: bool = False,
    ) -> dict[str, Any]:
        option, binding_error = validate_recovery_option_binding(
            self.recovery_store,
            recovery_event,
            recovery_id,
            "kernel_discard_or_archive_staged_work",
        )
        if binding_error is not None:
            return _rejected(
                self.recovery_store,
                recovery_event,
                recovery_id,
                staged_work_ref,
                binding_error,
            )

        if destructive and not confirmation_ref:
            return _rejected(
                self.recovery_store,
                recovery_event,
                recovery_id,
                staged_work_ref,
                "destructive_confirmation_missing",
            )
        if destructive and not scope_is_explicit:
            return _rejected(
                self.recovery_store,
                recovery_event,
                recovery_id,
                staged_work_ref,
                "destructive_scope_not_explicit",
            )
        if destructive and option is not None and option.get("requires_confirmation") is not True:
            return _rejected(
                self.recovery_store,
                recovery_event,
                recovery_id,
                staged_work_ref,
                "destructive_scope_not_bound_to_recovery_option",
            )
        if targets_active_production and not destructive:
            return _rejected(
                self.recovery_store,
                recovery_event,
                recovery_id,
                staged_work_ref,
                "active_production_data_requires_destructive_scope",
            )
        if targets_active_production and destructive and not scope_is_explicit:
            return _rejected(
                self.recovery_store,
                recovery_event,
                recovery_id,
                staged_work_ref,
                "active_production_data_requires_explicit_scope",
            )

        archive_id = generate_id("recovery_event_id").replace("rev_", "arc_", 1)
        archive_path = self.paths.state_root / "archive" / "staged_work" / archive_id / "archive_manifest.json"
        manifest = {
            "archive_id": archive_id,
            "archived_refs": [{"archive_ref": staged_work_ref}],
            "affected_recovery_event_ids": [recovery_event["recovery_event_id"]],
            "affected_workflow_run_ids": [recovery_event["workflow_run_id"]],
            "created_at": utc_iso(),
            "destructive": destructive,
            "original_refs": [dict(ref) for ref in original_refs],
            "preserved_receipts": [{"recovery_event_id": recovery_event["recovery_event_id"]}],
            "schema_version": "repository.staged_work_archive.v1",
            "user_confirmation_refs": [dict(confirmation_ref)] if confirmation_ref else [],
        }
        self._json.write_json(archive_path, manifest)
        receipt = self.recovery_store.append_recovery_receipt(
            recovery_event=recovery_event,
            recovery_id=recovery_id,
            result_status=RecoveryResultStatus.APPLIED.value,
            selected_recovery_option={"staged_work_ref": staged_work_ref},
            written_refs=[{"archive_path": self.paths.relative_to_state_root(archive_path)}],
            mutated_refs=[],
            user_confirmation_refs=[dict(confirmation_ref)] if confirmation_ref else [],
        )
        return {
            "archive_ref": {"archive_id": archive_id, "archive_path": self.paths.relative_to_state_root(archive_path)},
            "discard_receipt_id": receipt.payload["recovery_receipt_id"] if destructive else None,
            "receipt": receipt,
            "result_status": "applied",
        }


def _rejected(
    recovery_store: RecoveryEventStore,
    recovery_event: Mapping[str, Any],
    recovery_id: str,
    staged_work_ref: str,
    reason: str,
) -> dict[str, Any]:
    receipt = recovery_store.append_recovery_receipt(
        recovery_event=recovery_event,
        recovery_id=recovery_id,
        result_status=RecoveryResultStatus.REJECTED.value,
        selected_recovery_option={"staged_work_ref": staged_work_ref, "reason": reason},
    )
    return {
        "archive_ref": None,
        "discard_receipt_id": None,
        "receipt": receipt,
        "result_status": "rejected",
    }
