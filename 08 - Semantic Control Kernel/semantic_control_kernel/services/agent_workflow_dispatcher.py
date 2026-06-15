from __future__ import annotations

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_workflow_constants import CREATION_CONTINUATION_TOOL_NAMES
from semantic_control_kernel.services.agent_workflow_creation_runner import run_database_creation_agent_workflow
from semantic_control_kernel.services.agent_workflow_manual_pipeline_runner import run_manual_pipeline_agent_workflow
from semantic_control_kernel.services.agent_workflow_merge_runner import run_database_merge_agent_workflow
from semantic_control_kernel.services.agent_workflow_rebuild_runner import run_database_rebuild_agent_workflow
from semantic_control_kernel.services.agent_workflow_reset_runner import run_database_reset_agent_workflow
from semantic_control_kernel.services.agent_workflow_results import missing_kernel_state_result
from semantic_control_kernel.services.resume_options import RESUME_CONTINUE_TOOL_NAME
from semantic_control_kernel.types.agent_tools import AgentToolResult


def dispatch_permanent_workflow_tool(
    tool_name: str,
    *,
    state_paths: StatePaths,
    database_creation_runtime,
    pipeline_runtime,
    merge_runtime,
    rebuild_runtime,
    result_from_execution,
) -> AgentToolResult:
    if tool_name in CREATION_CONTINUATION_TOOL_NAMES:
        return AgentToolResult(
            tool_name=tool_name,
            status="blocked",
            effect="none",
            user_visible_summary="Continuation routes require an explicit Kernel resume option and cannot be started directly.",
            active_state={
                "next_agent_tool": RESUME_CONTINUE_TOOL_NAME,
                "resume_state_tool": "kernel_resume_state",
                "blocked_reason": "continuation_route_requires_resume_option",
            },
            error={
                "code": "continuation_requires_resume_option",
                "message": "Call kernel_resume_state and choose a resume_option_ref before continuing this route.",
            },
        )
    if tool_name.startswith("empty_database_"):
        execution = run_database_creation_agent_workflow(
            tool_name,
            state_paths=state_paths,
            database_creation_runtime=database_creation_runtime,
        ).to_dict()
        return result_from_execution(tool_name, execution, state_paths=state_paths)
    if tool_name == "manual_pipeline_run":
        execution = run_manual_pipeline_agent_workflow(
            state_paths=state_paths,
            pipeline_runtime=pipeline_runtime,
        ).to_dict()
        return result_from_execution(tool_name, execution, state_paths=state_paths)
    if tool_name == "reset_database":
        execution = run_database_reset_agent_workflow(
            state_paths=state_paths,
            pipeline_runtime=pipeline_runtime,
        ).to_dict()
        return result_from_execution(tool_name, execution, state_paths=state_paths)
    if tool_name == "database_merge_additive_only":
        execution = run_database_merge_agent_workflow(
            state_paths=state_paths,
            merge_runtime=merge_runtime,
        ).to_dict()
        return result_from_execution(tool_name, execution, state_paths=state_paths)
    if tool_name in {"empty_databases_merge_path", "filled_databases_merge_path"}:
        return missing_kernel_state_result(
            tool_name,
            "Merge selection must be collected through Kernel/UI state before the concrete merge path can continue.",
        )
    if tool_name == "database_rebuild_from_artifacts":
        execution = run_database_rebuild_agent_workflow(
            state_paths=state_paths,
            rebuild_runtime=rebuild_runtime,
        ).to_dict()
        return result_from_execution(tool_name, execution, state_paths=state_paths)
    return AgentToolResult(
        tool_name=tool_name,
        status="rejected",
        effect="none",
        user_visible_summary="The selected Agent-facing workflow tool is not routable in the current Kernel build.",
        error={
            "code": "unknown_action",
            "message": "The selected Agent-facing workflow tool is not routable in the current Kernel build.",
        },
    )
