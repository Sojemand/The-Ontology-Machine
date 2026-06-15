from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.workflows.database_creation.shared_steps import create_blocker


def call_semantic_adapter(
    adapter: Any,
    method_names: tuple[str, ...],
    payload: Mapping[str, Any],
    *,
    step_id: str,
    function_name: str,
) -> object:
    for method_name in method_names:
        method = getattr(adapter, method_name, None)
        if method is not None:
            return method(payload)
    return create_blocker(
        step_id=step_id,
        function_or_route=function_name,
        blocker_code="pipeline_capability_missing",
        recovery_state_class="support_only_unrecoverable",
        summary=f"SemanticReleaseAdapter method for {function_name} is unavailable.",
    )
