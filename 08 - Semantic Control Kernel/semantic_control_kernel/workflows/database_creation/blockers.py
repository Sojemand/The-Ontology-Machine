from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.adapter_results import MissingCapabilityBlocker
from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker


def create_blocker(
    *,
    step_id: str,
    function_or_route: str,
    blocker_code: str,
    summary: str,
    recovery_state_class: str = "support_only_unrecoverable",
    diagnostics: Sequence[Mapping[str, Any]] = (),
) -> DatabaseCreationBlocker:
    return DatabaseCreationBlocker(
        blocker_code=blocker_code,
        step_id=step_id,
        function_or_route=function_or_route,
        recovery_state_class=recovery_state_class,
        user_visible_summary=summary,
        diagnostics=tuple(dict(item) for item in diagnostics),
    )


def blocker_from_missing_capability(step_id: str, blocker: MissingCapabilityBlocker) -> DatabaseCreationBlocker:
    payload = blocker.to_dict()
    return create_blocker(
        step_id=step_id,
        function_or_route=str(payload.get("kernel_function", "")),
        blocker_code="pipeline_capability_missing",
        recovery_state_class=str(payload.get("recovery_state_class", "support_only_unrecoverable")),
        summary=str(payload.get("blocking_reason", "Required Pipeline capability is not available.")),
        diagnostics=payload.get("diagnostics", ()),
    )
