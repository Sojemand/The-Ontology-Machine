from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _availability(mode: str, first_tool: str | None = None, **extra: Any) -> dict[str, Any]:
    payload = {"mode": mode, "direct_agent_tool_available": mode.startswith("agent_tool")}
    if first_tool:
        payload["first_agent_tool"] = first_tool
    payload.update(extra)
    return payload


def _tool(option_id: str, label: str, meaning: str, first_tool: str) -> dict[str, Any]:
    return {
        "option_id": option_id,
        "user_label": label,
        "meaning": meaning,
        "surface_availability": _availability("agent_tool", first_tool),
    }


def _no_semantic_release_next_step_options() -> list[Mapping[str, Any]]:
    return [
        {
            "option_id": "attach_default_semantic_release",
            "user_label": "Attach default Semantic Release",
            "meaning": "Use the built-in default taxonomy and default projections so the empty database becomes semantically runnable.",
            "surface_availability": _availability(
                "explicit_kernel_resume_selection",
                "kernel_resume_state",
                direct_agent_tool_available=False,
                continuation_workflow_tool="empty_database_default_taxonomy_default_projections",
                requires_explicit_resume_selection=True,
                resume_step_id="dc_export_default_release",
            ),
            "result_if_completed": {"final_state": "semantic_release_active", "database_ready_for_ingest": True},
        },
        {
            "option_id": "create_custom_taxonomy_then_projection",
            "user_label": "Create custom taxonomy, then custom projections",
            "meaning": "Author a custom taxonomy from sample files first, then create projections against that taxonomy.",
            "prerequisites": {
                "sample_evidence_required": True,
                "sample_evidence_location": "Artifact Tree Input folder, confirmed through select_sample_files",
            },
            "surface_availability": _availability(
                "explicit_kernel_resume_selection",
                "kernel_resume_state",
                direct_agent_tool_available=False,
                continuation_workflow_tool="create_custom_taxonomy_path",
                required_followup_agent_tool="create_custom_projection_path",
                requires_explicit_resume_selection=True,
            ),
            "result_if_only_first_step_completed": {"final_state": "semantic_release_incomplete", "database_ready_for_ingest": False},
            "result_if_full_chain_completed": {"final_state": "semantic_release_active", "database_ready_for_ingest": True},
        },
    ]


def _blocked_inspection_next_step_options() -> list[Mapping[str, Any]]:
    return [
        _tool("kernel_status", "Inspect Kernel status", "Read the latest Kernel state, blocker and resumable workflow options.", "kernel_status"),
        _tool("inspect_resume_state", "Inspect resume state", "List explicit Kernel resume options before continuing projection authoring.", "kernel_resume_state"),
    ]


def _projectionless_next_step_options(*, taxonomy_label: str = "staged default taxonomy") -> list[Mapping[str, Any]]:
    return [
        {
            "option_id": "create_custom_projection_path",
            "user_label": "Create custom projections",
            "meaning": f"Author custom projections against the {taxonomy_label}, then write, attach and activate the resulting complete Semantic Release.",
            "surface_availability": _availability(
                "explicit_kernel_resume_selection",
                "kernel_resume_state",
                direct_agent_tool_available=False,
                continuation_workflow_tool="create_custom_projection_path",
                requires_explicit_resume_selection=True,
                resume_step_id="proj_require_taxonomy",
            ),
            "result_if_completed": {"final_state": "semantic_release_active", "database_ready_for_ingest": True},
        }
    ]


def _ready_default_release_next_step_options() -> list[Mapping[str, Any]]:
    return [
        _tool("manual_pipeline_run", "Run ingestion", "Ingest files from the active Artifact Tree Input folder into the ready database.", "manual_pipeline_run"),
        _tool("kernel_status", "Inspect status", "Read the current Kernel state and active target details.", "kernel_status"),
    ]
