from __future__ import annotations

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.services.agent_workflow_constants import CREATION_CONTINUATION_TOOL_NAMES
from semantic_control_kernel.services.agent_database_creation_resume import continue_database_creation_resume_option
from semantic_control_kernel.services.agent_workflow_creation_runner import (
    run_database_creation_agent_workflow,
)
from semantic_control_kernel.services.agent_workflow_manual_pipeline_runner import run_manual_pipeline_agent_workflow
from semantic_control_kernel.services.agent_workflow_merge_runner import run_database_merge_agent_workflow
from semantic_control_kernel.services.agent_workflow_rebuild_runner import run_database_rebuild_agent_workflow
from semantic_control_kernel.services.agent_workflow_reset_runner import run_database_reset_agent_workflow
from semantic_control_kernel.services.resume_options import (
    RESUME_CONTINUE_TOOL_NAME,
    ResumeOption,
    list_resume_options,
    resolve_resume_option,
)
from semantic_control_kernel.types.agent_tools import AgentToolResult


def continue_resumable_workflow(
    resume_option_ref: str | None,
    *,
    state_paths: StatePaths,
    database_creation_runtime,
    result_from_execution,
) -> AgentToolResult:
    store = WorkflowResumeStore(state_paths)
    options = list_resume_options(store)
    selected_ref = str(resume_option_ref or "").strip()
    if selected_ref:
        option = resolve_resume_option(store, selected_ref)
        if option is None:
            return _resume_option_not_available(options)
    elif len(options) == 1:
        option = options[0]
    else:
        return AgentToolResult(
            tool_name=RESUME_CONTINUE_TOOL_NAME,
            status="blocked",
            effect="none",
            user_visible_summary="A specific Kernel resume option is required before a workflow can be continued.",
            error={
                "code": "resume_option_ref_required",
                "message": "Call kernel_resume_state and choose one returned resume_option_ref before continuing.",
            },
            active_state={
                "resume_options": [item.to_dict() for item in options],
                "next_agent_tool": RESUME_CONTINUE_TOOL_NAME,
            },
        )
    if option.resume_family != "database_creation" or option.database_creation_context is None:
        return AgentToolResult(
            tool_name=RESUME_CONTINUE_TOOL_NAME,
            status="blocked",
            effect="none",
            user_visible_summary="The selected resume family is not executable by the current Kernel build.",
            error={
                "code": "resume_family_not_supported",
                "message": "The selected resume family is not executable by the current Kernel build.",
            },
            active_state={"resume_option": option.to_dict()},
        )
    return continue_database_creation_resume_option(
        option,
        state_paths=state_paths,
        store=store,
        database_creation_runtime=database_creation_runtime,
        result_from_execution=result_from_execution,
    )


def continue_workflow_after_interaction(
    *,
    workflow_run_id: str,
    workflow_tool: str,
    state_paths: StatePaths,
    database_creation_runtime,
    pipeline_runtime,
    merge_runtime,
    rebuild_runtime,
    result_from_execution,
) -> AgentToolResult | None:
    if workflow_tool == "database_merge_additive_only":
        execution = run_database_merge_agent_workflow(
            state_paths=state_paths,
            merge_runtime=merge_runtime,
            workflow_run_id=workflow_run_id,
        ).to_dict()
        return result_from_execution(workflow_tool, execution, state_paths=state_paths)
    if workflow_tool == "database_rebuild_from_artifacts":
        execution = run_database_rebuild_agent_workflow(
            state_paths=state_paths,
            rebuild_runtime=rebuild_runtime,
            workflow_run_id=workflow_run_id,
        ).to_dict()
        return result_from_execution(workflow_tool, execution, state_paths=state_paths)
    if workflow_tool == "reset_database":
        execution = run_database_reset_agent_workflow(
            state_paths=state_paths,
            pipeline_runtime=pipeline_runtime,
            workflow_run_id=workflow_run_id,
        ).to_dict()
        return result_from_execution(workflow_tool, execution, state_paths=state_paths)
    if workflow_tool == "manual_pipeline_run":
        execution = run_manual_pipeline_agent_workflow(
            state_paths=state_paths,
            pipeline_runtime=pipeline_runtime,
            workflow_run_id=workflow_run_id,
        ).to_dict()
        return result_from_execution(workflow_tool, execution, state_paths=state_paths)
    if not workflow_tool.startswith("empty_database_") and workflow_tool not in CREATION_CONTINUATION_TOOL_NAMES:
        return None
    execution = run_database_creation_agent_workflow(
        workflow_tool,
        state_paths=state_paths,
        database_creation_runtime=database_creation_runtime,
        workflow_run_id=workflow_run_id,
        resume_from_progress=True,
    ).to_dict()
    return result_from_execution(workflow_tool, execution, state_paths=state_paths)


def _resume_option_not_available(options: list[ResumeOption]) -> AgentToolResult:
    return AgentToolResult(
        tool_name=RESUME_CONTINUE_TOOL_NAME,
        status="rejected",
        effect="none",
        user_visible_summary="The selected Kernel resume option is no longer available.",
        error={
            "code": "resume_option_not_available",
            "message": "The selected Kernel resume option is no longer available.",
        },
        active_state={"resume_options": [item.to_dict() for item in options]},
    )
