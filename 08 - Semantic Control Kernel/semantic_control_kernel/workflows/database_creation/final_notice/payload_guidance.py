from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from semantic_control_kernel.workflows.database_creation.final_notice.constants import (
    _DEFAULT_COMPLETION_STRUCTURE,
    _RESUMED_COMPLETION_STRUCTURE,
)
from semantic_control_kernel.workflows.explanation_context import explanation_preferred_structure

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution


def _agent_guidance(
    execution: "DatabaseCreationExecution" | None = None,
    context: Mapping[str, Any] | None = None,
    *,
    goal: str,
    style: str,
    default_structure: list[str] | None = None,
    resumed_structure: list[str] | None = None,
    preferred_structure: list[str] | None = None,
    must_include: list[str],
    focus_path: str,
    next_step_instruction: Mapping[str, Any],
    do_not_claim: list[str] | None = None,
    workflow_explanation_context_path: str | None = None,
) -> dict[str, Any]:
    from semantic_control_kernel.workflows.database_creation.final_notice.payload_artifacts import _workflow_explanation_context

    if context is None:
        context = _workflow_explanation_context(execution) if execution is not None else {}
    structure = preferred_structure or explanation_preferred_structure(
        context,
        default_structure=default_structure or _DEFAULT_COMPLETION_STRUCTURE,
        resumed_structure=resumed_structure or _RESUMED_COMPLETION_STRUCTURE,
    )
    payload = {
        "response_mode": "explain_now",
        "goal": goal,
        "audience": "pipeline_user",
        "style": style,
        "preferred_structure": structure,
        "must_include": must_include,
        "use_technical_detail_ref": True,
        "technical_detail_focus_path": focus_path,
        "next_step_instruction": dict(next_step_instruction),
    }
    if workflow_explanation_context_path is not None or execution is not None:
        payload["workflow_explanation_context_path"] = workflow_explanation_context_path or f"{focus_path}.workflow_explanation_context"
        payload["must_distinguish_provenance"] = ["already_available", "performed_this_run", "current_state_summary"]
    if do_not_claim:
        payload["do_not_claim"] = list(do_not_claim)
    return payload


def _with_provenance_do_not_claim(claims: list[str], context: Mapping[str, Any]) -> list[str]:
    return claims + (
        [
            "that already_available workflow state was newly performed in this run",
            "that paths from unchanged_artifacts were recreated instead of reused",
        ]
        if context.get("already_available")
        else []
    )
