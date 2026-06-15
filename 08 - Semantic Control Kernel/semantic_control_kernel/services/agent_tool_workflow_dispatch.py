from __future__ import annotations

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_workflow_constants import CREATION_CONTINUATION_TOOL_NAMES
from semantic_control_kernel.services.agent_workflow_dispatcher import dispatch_permanent_workflow_tool as _dispatch_permanent_workflow_tool
from semantic_control_kernel.services.agent_workflow_results import result_from_execution as _result_from_execution
from semantic_control_kernel.services.agent_workflow_resume import (
    continue_resumable_workflow as _continue_resumable_workflow,
    continue_workflow_after_interaction as _continue_workflow_after_interaction,
)
from semantic_control_kernel.services.agent_workflow_runtimes import (
    database_creation_runtime as _database_creation_runtime,
    merge_runtime as _merge_runtime,
    pipeline_root_for as _pipeline_root,
    pipeline_runtime as _pipeline_runtime,
    rebuild_runtime as _rebuild_runtime,
)
from semantic_control_kernel.types.agent_tools import AgentToolResult


def continue_resumable_workflow(
    resume_option_ref: str | None,
    *,
    state_paths: StatePaths,
) -> AgentToolResult:
    return _continue_resumable_workflow(
        resume_option_ref,
        state_paths=state_paths,
        database_creation_runtime=_database_creation_runtime,
        result_from_execution=_result_from_execution,
    )


def dispatch_permanent_workflow_tool(tool_name: str, *, state_paths: StatePaths) -> AgentToolResult:
    return _dispatch_permanent_workflow_tool(
        tool_name,
        state_paths=state_paths,
        database_creation_runtime=_database_creation_runtime,
        pipeline_runtime=_pipeline_runtime,
        merge_runtime=_merge_runtime,
        rebuild_runtime=_rebuild_runtime,
        result_from_execution=_result_from_execution,
    )


def continue_workflow_after_interaction(
    *,
    workflow_run_id: str,
    workflow_tool: str,
    state_paths: StatePaths,
) -> AgentToolResult | None:
    return _continue_workflow_after_interaction(
        workflow_run_id=workflow_run_id,
        workflow_tool=workflow_tool,
        state_paths=state_paths,
        database_creation_runtime=_database_creation_runtime,
        pipeline_runtime=_pipeline_runtime,
        merge_runtime=_merge_runtime,
        rebuild_runtime=_rebuild_runtime,
        result_from_execution=_result_from_execution,
    )


__all__ = [
    "CREATION_CONTINUATION_TOOL_NAMES",
    "_database_creation_runtime",
    "_merge_runtime",
    "_pipeline_root",
    "_pipeline_runtime",
    "_rebuild_runtime",
    "_result_from_execution",
    "continue_resumable_workflow",
    "continue_workflow_after_interaction",
    "dispatch_permanent_workflow_tool",
]
