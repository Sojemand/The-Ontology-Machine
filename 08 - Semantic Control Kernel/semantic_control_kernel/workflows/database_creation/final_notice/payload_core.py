from __future__ import annotations

from typing import TYPE_CHECKING, Any

from semantic_control_kernel.workflows.database_creation.final_notice.constants import (
    _DEFAULT_BLOCKED_STRUCTURE,
    _DEFAULT_COMPLETION_STRUCTURE,
    _RESUMED_BLOCKED_STRUCTURE,
    _RESUMED_COMPLETION_STRUCTURE,
)
from semantic_control_kernel.workflows.database_creation.final_notice.payload_artifacts import (
    _created_artifacts,
    _workflow_explanation_context,
)
from semantic_control_kernel.workflows.database_creation.final_notice.payload_blockers import _blocker_payload
from semantic_control_kernel.workflows.database_creation.final_notice.payload_guidance import (
    _agent_guidance,
    _with_provenance_do_not_claim,
)

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution


def _completion_payload(execution: "DatabaseCreationExecution", **kwargs: Any) -> dict[str, Any]:
    context = _workflow_explanation_context(execution)
    return {
        "agent_explanation_guidance": _agent_guidance(
            execution,
            context,
            goal=kwargs["guidance_goal"],
            style=kwargs["guidance_style"],
            default_structure=_DEFAULT_COMPLETION_STRUCTURE,
            resumed_structure=_RESUMED_COMPLETION_STRUCTURE,
            must_include=kwargs["guidance_must_include"],
            focus_path="technical_detail_ref.workflow_completion",
            next_step_instruction=kwargs["next_step_instruction"],
            do_not_claim=_with_provenance_do_not_claim(kwargs["do_not_claim"], context),
        ),
        "technical_detail_ref": {
            "kind": "database_creation_workflow_completion",
            "workflow_completion": {
                "workflow_family": "database_creation",
                "workflow_tool": execution.workflow_tool,
                "final_state": execution.final_state,
                "decision_required": kwargs["decision_required"],
                "decision_prompt": kwargs["decision_prompt"],
                "outcome": dict(kwargs["outcome"]),
                "created_artifacts": _created_artifacts(execution),
                "workflow_explanation_context": context,
                "kernel_persistence": dict(kwargs["kernel_persistence"]),
                "state_meaning": dict(kwargs["state_meaning"]),
                "next_step_options": [dict(item) for item in kwargs["next_step_options"]],
            },
        },
    }


def _blocked_payload(execution: "DatabaseCreationExecution", **kwargs: Any) -> dict[str, Any]:
    context = _workflow_explanation_context(execution)
    blocked = {
        "workflow_family": "database_creation",
        "workflow_tool": execution.workflow_tool,
        "final_state": execution.final_state,
        "blocker": _blocker_payload(execution),
        "outcome": dict(kwargs["outcome"]),
        "created_artifacts": _created_artifacts(execution),
        "workflow_explanation_context": context,
        "kernel_persistence": dict(kwargs["kernel_persistence"]),
        "state_meaning": dict(kwargs["state_meaning"]),
        "next_step_options": [dict(item) for item in kwargs["next_step_options"]],
        **dict(kwargs["extra_blocked_fields"]),
    }
    return {
        "agent_explanation_guidance": _agent_guidance(
            execution,
            context,
            goal=kwargs["guidance_goal"],
            style="brief_operational_summary_with_blocker_and_next_steps",
            default_structure=_DEFAULT_BLOCKED_STRUCTURE,
            resumed_structure=_RESUMED_BLOCKED_STRUCTURE,
            must_include=kwargs["guidance_must_include"],
            focus_path="technical_detail_ref.workflow_blocked",
            next_step_instruction={"explain_blocker_meaning": True, "explain_surface_availability": True, "mention_that_ingest_is_not_ready": True},
            do_not_claim=_with_provenance_do_not_claim([], context),
        ),
        "technical_detail_ref": {"kind": "database_creation_workflow_blocked", "workflow_blocked": blocked},
    }
