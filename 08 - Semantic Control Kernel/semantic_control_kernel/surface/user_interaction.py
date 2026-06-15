from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.services.user_interaction_service import (
    InteractionDispatchResult,
    InteractionResponseResult,
    KernelUserInteractionService,
)
from semantic_control_kernel.types.events import UserInteractionResponse
from semantic_control_kernel.types.interaction import validate_user_interaction_response


def open_user_interaction(
    service: KernelUserInteractionService,
    *,
    interaction_function: str,
    workflow_run_id: str,
    function_or_route: str,
    target_identity: Mapping[str, Any],
    state_snapshot_identity: Mapping[str, Any],
    user_visible_title: str,
    user_visible_summary: str,
    **kwargs: Any,
) -> InteractionDispatchResult:
    return service.request_interaction(
        interaction_function=interaction_function,
        workflow_run_id=workflow_run_id,
        function_or_route=function_or_route,
        target_identity=target_identity,
        state_snapshot_identity=state_snapshot_identity,
        user_visible_title=user_visible_title,
        user_visible_summary=user_visible_summary,
        **kwargs,
    )


def submit_user_interaction_response(
    service: KernelUserInteractionService,
    payload: Mapping[str, Any],
) -> InteractionResponseResult:
    validate_user_interaction_response(payload)
    return service.submit_response(UserInteractionResponse.from_dict(payload))
