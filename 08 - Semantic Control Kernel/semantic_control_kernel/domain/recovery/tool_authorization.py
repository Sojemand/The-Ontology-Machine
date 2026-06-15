from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.validation.contract_validation import KernelContractError
from semantic_control_kernel.validation.recovery_validation import assert_recovery_mirror_event


@dataclass(frozen=True)
class RecoveryToolAuthorizationResult:
    allowed: bool
    reason: str = ""
    recovery_event: Mapping[str, Any] | None = None
    recovery_option: Mapping[str, Any] | None = None


class RecoveryToolAuthorization:
    def __init__(self, recovery_store: RecoveryEventStore, mirror_store: MirrorEventStore) -> None:
        self.recovery_store = recovery_store
        self.mirror_store = mirror_store

    def authorize(
        self,
        *,
        tool_name: str,
        mirror_event_id: str,
        recovery_event_id: str,
        recovery_id: str,
    ) -> RecoveryToolAuthorizationResult:
        try:
            recovery_event = self.recovery_store.get_recovery_event(recovery_event_id).to_dict()
            mirror_event = self.mirror_store.get_mirror_event(mirror_event_id).to_dict()
            availability = self.mirror_store.get_tool_availability(mirror_event_id).to_dict()
            option = self.recovery_store.get_option(recovery_event_id, recovery_id).to_dict()
        except ResumeStateNotFoundError as exc:
            return RecoveryToolAuthorizationResult(False, str(exc))

        try:
            assert_recovery_mirror_event(mirror_event)
        except KernelContractError:
            return RecoveryToolAuthorizationResult(False, "mirror_event_invalid", recovery_event, option)
        if mirror_event.get("mirror_event_id") != recovery_event.get("mirror_event_id"):
            return RecoveryToolAuthorizationResult(False, "mirror_event_mismatch", recovery_event, option)
        if recovery_event.get("status") not in {"active", "support_only"}:
            return RecoveryToolAuthorizationResult(False, f"recovery_event_{recovery_event.get('status')}", recovery_event, option)
        if availability.get("status") != "active":
            return RecoveryToolAuthorizationResult(False, f"tool_availability_{availability.get('status')}", recovery_event, option)
        if _is_expired(availability.get("expires_at")) or _is_expired(recovery_event.get("expires_at")):
            return RecoveryToolAuthorizationResult(False, "event_expired", recovery_event, option)
        if tool_name not in mirror_event.get("allowed_agent_tools", []):
            return RecoveryToolAuthorizationResult(False, "tool_not_allowed_by_mirror", recovery_event, option)
        if tool_name not in recovery_event.get("allowed_agent_tools", []):
            return RecoveryToolAuthorizationResult(False, "tool_not_allowed_for_event", recovery_event, option)
        if tool_name not in availability.get("allowed_agent_tools", []):
            return RecoveryToolAuthorizationResult(False, "tool_not_available_for_mirror", recovery_event, option)
        if option.get("recovery_event_id") != recovery_event_id:
            return RecoveryToolAuthorizationResult(False, "recovery_id_cross_event", recovery_event, option)
        if option.get("agent_tool") not in {tool_name, None}:
            return RecoveryToolAuthorizationResult(False, "recovery_id_bound_to_different_tool", recovery_event, option)
        if option.get("target_identity") != recovery_event.get("target_identity"):
            return RecoveryToolAuthorizationResult(False, "target_identity_changed", recovery_event, option)
        if option.get("state_snapshot_identity") != recovery_event.get("state_snapshot_identity"):
            return RecoveryToolAuthorizationResult(False, "state_snapshot_changed", recovery_event, option)
        return RecoveryToolAuthorizationResult(True, "", recovery_event, option)

    def expire(self, mirror_event_id: str, reason: str):
        return self.mirror_store.mark_event_scoped_tools_expired(mirror_event_id, reason)


def validate_recovery_option_binding(
    recovery_store: RecoveryEventStore,
    recovery_event: Mapping[str, Any],
    recovery_id: str,
    expected_tool_name: str,
) -> tuple[Mapping[str, Any] | None, str | None]:
    if recovery_event.get("status") not in {"active", "support_only"}:
        return None, f"recovery_event_{recovery_event.get('status')}"
    if expected_tool_name not in recovery_event.get("allowed_agent_tools", []):
        return None, "tool_not_allowed_for_event"
    try:
        option = recovery_store.get_option(str(recovery_event["recovery_event_id"]), recovery_id).to_dict()
    except ResumeStateNotFoundError:
        return None, "recovery_id_not_found"
    if option.get("recovery_event_id") != recovery_event.get("recovery_event_id"):
        return None, "recovery_id_cross_event"
    if option.get("agent_tool") != expected_tool_name:
        return None, "recovery_id_bound_to_different_tool"
    if option.get("target_identity") != recovery_event.get("target_identity"):
        return None, "target_identity_changed"
    if option.get("state_snapshot_identity") != recovery_event.get("state_snapshot_identity"):
        return None, "state_snapshot_changed"
    return option, None


def _is_expired(value: object) -> bool:
    if value is None:
        return False
    if not isinstance(value, str) or not value:
        return True
    return datetime.fromisoformat(value.replace("Z", "+00:00")) <= datetime.now(timezone.utc)
