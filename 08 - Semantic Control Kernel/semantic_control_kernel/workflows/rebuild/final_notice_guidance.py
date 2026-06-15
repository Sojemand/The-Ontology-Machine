from __future__ import annotations

from typing import Any

COMPLETION_ACTIONS: tuple[str, ...] = (
    "manual_pipeline_run",
    "kernel_status",
)


def agent_guidance(*, focus: str, blocked: bool) -> dict[str, Any]:
    return {
        "response_mode": "explain_now",
        "technical_detail_focus_path": f"technical_detail_ref.{focus}",
        "workflow_explanation_context_path": f"technical_detail_ref.{focus}.workflow_explanation_context",
        "goal": (
            "Explain why the Kernel database-rebuild run stopped and name the proven state."
            if blocked
            else "Explain that the Kernel database-rebuild run is finished and name what was rebuilt."
        ),
        "style": "brief_operational_summary_with_blocker_and_next_steps"
        if blocked
        else "brief_operational_summary_with_done_state",
        "must_include": (
            ["workflow_blocked", "final_state", "blocker", "target_database_path"]
            if blocked
            else ["workflow_completed", "final_state", "target_database_path", "created_artifacts"]
        ),
        "next_step_instruction": {"explain_blocker_meaning": True}
        if blocked
        else {"state_that_work_is_finished": True, "include_created_artifact_paths": True},
        "do_not_claim": (
            ["that the rebuild completed successfully"]
            if blocked
            else ["that a Kernel dialog is still waiting for input", "that the workflow is still running"]
        ),
    }
