from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from semantic_control_kernel.types.enums import RecoveryStateClass


DEFAULT_RECOVERY_EVENT_TTL_SECONDS = 30 * 60
SUPPORT_ONLY_RECOVERY_EVENT_TTL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class RecoveryPolicy:
    default_ttl_seconds: int = DEFAULT_RECOVERY_EVENT_TTL_SECONDS
    support_only_ttl_seconds: int = SUPPORT_ONLY_RECOVERY_EVENT_TTL_SECONDS

    def expires_at(self, recovery_state: str) -> str:
        ttl = (
            self.support_only_ttl_seconds
            if recovery_state == RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value
            else self.default_ttl_seconds
        )
        return (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat().replace("+00:00", "Z")

    def allows_event_tool(
        self,
        *,
        tool_name: str,
        recovery_state: str,
        target_identity_valid: bool = True,
        state_snapshot_valid: bool = True,
        required_receipt_present: bool = True,
        lock_proof_present: bool = True,
    ) -> bool:
        if not all((target_identity_valid, state_snapshot_valid, required_receipt_present, lock_proof_present)):
            return False
        if recovery_state == RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value:
            return tool_name in {
                "kernel_open_support_bundle",
                "kernel_cancel_active_run",
                "kernel_discard_or_archive_staged_work",
            }
        return bool(tool_name)

    def support_only_needed(self, evidence: Mapping[str, Any]) -> bool:
        return evidence.get("safe_recovery_available") is False or evidence.get("missing_capability") is True
