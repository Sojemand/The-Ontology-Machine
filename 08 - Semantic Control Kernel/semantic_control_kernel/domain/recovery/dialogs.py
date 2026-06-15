from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.ids import generate_id


class RecoveryDialogService:
    def open_dialog(self, recovery_event: Mapping[str, Any], recovery_option: Mapping[str, Any]) -> dict[str, Any]:
        dialog_action = recovery_option.get("kernel_dialog_action") or "recovery_dialog"
        return {
            "dialog_request_ref": {
                "dialog_request_id": generate_id("interaction_request_id"),
                "recovery_event_id": recovery_event["recovery_event_id"],
                "recovery_id": recovery_option["recovery_id"],
            },
            "kernel_dialog_state": {
                "dialog_action": dialog_action,
                "recovery_event_id": recovery_event["recovery_event_id"],
                "target_identity": dict(recovery_event["target_identity"]),
                "state_snapshot_identity": dict(recovery_event["state_snapshot_identity"]),
            },
        }
