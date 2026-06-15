from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.types.database_creation import DatabaseCreationResumeContext
from semantic_control_kernel.types.resume import RESUME_OPTION_SCHEMA_VERSION
from semantic_control_kernel.types.state import WorkflowResumeState
from semantic_control_kernel.workflows.database_creation.resume import extract_database_creation_resume_context


RESUME_CONTINUE_TOOL_NAME = "kernel_continue_resumable_workflow"


@dataclass(frozen=True)
class ResumeOption:
    resume_option_ref: str
    workflow_run_id: str
    workflow_ref: str
    resume_family: str
    source_workflow_tool: str
    continuation_workflow_tool: str
    state_snapshot_id: str
    target_identity: Mapping[str, Any]
    target_summary: Mapping[str, Any]
    label: str
    description: str
    effect: str
    risk_class: str
    database_creation_context: DatabaseCreationResumeContext | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RESUME_OPTION_SCHEMA_VERSION,
            "resume_option_ref": self.resume_option_ref,
            "workflow_ref": self.workflow_ref,
            "resume_family": self.resume_family,
            "source_workflow_tool": self.source_workflow_tool,
            "continuation_workflow_tool": self.continuation_workflow_tool,
            "state_snapshot_id": self.state_snapshot_id,
            "target_identity": dict(self.target_identity),
            "target_summary": dict(self.target_summary),
            "label": self.label,
            "description": self.description,
            "effect": self.effect,
            "risk_class": self.risk_class,
            "status": "available",
            "agent_tool": RESUME_CONTINUE_TOOL_NAME,
            "agent_instruction": "Call kernel_continue_resumable_workflow with this exact resume_option_ref.",
        }


def list_resume_options(store: WorkflowResumeStore | None) -> tuple[ResumeOption, ...]:
    if store is None:
        return ()
    options: list[ResumeOption] = []
    for state in store.list_resumable():
        options.extend(_options_for_state(state))
    return tuple(options)


def resolve_resume_option(store: WorkflowResumeStore | None, resume_option_ref: str) -> ResumeOption | None:
    expected = str(resume_option_ref or "").strip()
    if not expected:
        return None
    for option in list_resume_options(store):
        if option.resume_option_ref == expected:
            return option
    return None


def _options_for_state(state: WorkflowResumeState) -> tuple[ResumeOption, ...]:
    try:
        context = extract_database_creation_resume_context(state)
    except Exception:
        return ()
    return tuple(_database_creation_option(context, tool) for tool in context.allowed_continuation_workflow_tools)


def _database_creation_option(context: DatabaseCreationResumeContext, continuation_tool: str) -> ResumeOption:
    label, description, effect = _database_creation_copy(continuation_tool)
    return ResumeOption(
        resume_option_ref=_opaque_ref(
            "resume_option",
            context.workflow_run_id,
            context.state_snapshot_id,
            continuation_tool,
        ),
        workflow_run_id=context.workflow_run_id,
        workflow_ref=_opaque_ref("workflow", context.workflow_run_id),
        resume_family="database_creation",
        source_workflow_tool=context.workflow_tool,
        continuation_workflow_tool=continuation_tool,
        state_snapshot_id=context.state_snapshot_id,
        target_identity=dict(context.target_identity),
        target_summary=_database_creation_target_summary(context),
        label=label,
        description=description,
        effect=effect,
        risk_class="low",
        database_creation_context=context,
    )


def _database_creation_copy(continuation_tool: str) -> tuple[str, str, str]:
    if continuation_tool == "empty_database_default_taxonomy_default_projections":
        return (
            "Attach and activate the default Semantic Release",
            "Continue the existing empty database workflow by exporting, writing, attaching and activating the default taxonomy and projections.",
            "database_creation_resumed_to_default_ready_database",
        )
    if continuation_tool == "create_custom_taxonomy_path":
        return (
            "Create a custom taxonomy path",
            "Continue the existing database workflow into custom taxonomy authoring before projections and release activation.",
            "database_creation_resumed_to_custom_taxonomy_path",
        )
    if continuation_tool == "create_custom_projection_path":
        return (
            "Create custom projections path",
            "Continue the existing database workflow into custom projection authoring for the staged or active taxonomy.",
            "database_creation_resumed_to_custom_projection_path",
        )
    friendly = continuation_tool.replace("_", " ")
    return (
        friendly,
        f"Continue the existing database creation workflow with {friendly}.",
        "database_creation_resumed",
    )


def _database_creation_target_summary(context: DatabaseCreationResumeContext) -> dict[str, Any]:
    target = dict(context.target_payload or {})
    return {
        "artifact_root_name": str(target.get("artifact_root_name") or ""),
        "database_name": str(target.get("database_name") or ""),
        "final_state": context.final_state,
        "target_hash": str(context.target_identity.get("target_hash") or ""),
    }


def _opaque_ref(*parts: str) -> str:
    digest = hashlib.sha256(":".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return "opaque:" + digest[:24]
