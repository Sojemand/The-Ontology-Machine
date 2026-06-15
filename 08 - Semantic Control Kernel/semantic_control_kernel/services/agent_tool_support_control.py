from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.services.agent_tool_invocation_policy import string_or_none
from semantic_control_kernel.services.agent_tool_invocation_state import (
    active_run_summaries,
    opaque_ref,
    pending_interaction_count,
    pending_interactions_for_workflow,
    resumable_count,
    workflow_run_summary,
)
from semantic_control_kernel.services.agent_tool_workflow_dispatch import continue_resumable_workflow
from semantic_control_kernel.services.resume_options import RESUME_CONTINUE_TOOL_NAME, list_resume_options
from semantic_control_kernel.surface.background_continuation import terminate_background_continuations
from semantic_control_kernel.surface.client_frontend_continuation import append_background_continuation_terminal_progress
from semantic_control_kernel.types.agent_tools import AgentToolInvocation, AgentToolResult, blocked_result, ok_result, rejected_result


class AgentToolSupportControlMixin:
    def _kernel_status(self, invocation: AgentToolInvocation) -> AgentToolResult:
        active_runs = active_run_summaries(self.workflow_run_store)
        active_state = {
            "support_status": "read_only",
            "active_workflow_runs": active_runs,
            "active_workflow_run_count": len(active_runs),
            "resumable_workflow_count": resumable_count(self.resume_store),
            "pending_interaction_count": pending_interaction_count(self.interaction_store),
        }
        return ok_result(invocation.tool_name, effect="read", user_visible_summary="Kernel status was read without changing workflow state.", active_state=active_state)

    def _kernel_resume_state(self, invocation: AgentToolInvocation) -> AgentToolResult:
        resume_options = list_resume_options(self.resume_store)
        summaries = []
        if self.resume_store is not None:
            for state in self.resume_store.list_resumable():
                payload = state.to_dict()
                workflow_run_id = str(payload["workflow_run_id"])
                summaries.append(_resume_summary(payload, resume_options, pending_interactions_for_workflow(self.interaction_store, workflow_run_id)))
        return ok_result(
            invocation.tool_name,
            effect="read",
            user_visible_summary="Resumable Kernel workflow state was listed without resuming anything.",
            resume_state={
                "support_status": "read_only",
                "resumable_workflows": summaries,
                "resumable_count": len(summaries),
                "resume_options": [option.to_dict() for option in resume_options],
                "next_agent_tool": RESUME_CONTINUE_TOOL_NAME if resume_options else None,
                "id_policy": "kernel_ids_are_opaque",
            },
        )

    def _kernel_continue_resumable_workflow(self, invocation: AgentToolInvocation, model_values: Mapping[str, Any]) -> AgentToolResult:
        if self.state_paths is None:
            return blocked_result(invocation.tool_name, code="kernel_state_unavailable", message="The Kernel requires a resolved state root before it can continue a resumable workflow.")
        context_ref = string_or_none(invocation.invocation_context.get("resume_option_ref"))
        model_ref = string_or_none(model_values.get("resume_option_ref"))
        invalid = _invalid_resume_ref(invocation.invocation_context, context_ref) or _invalid_resume_ref(model_values, model_ref)
        if invalid:
            return rejected_result(invocation.tool_name, "resume_option_ref_invalid", "The resume option ref must be a non-empty opaque Kernel value.")
        if context_ref and model_ref and context_ref != model_ref:
            return rejected_result(invocation.tool_name, "resume_option_ref_mismatch", "The selected resume option ref differed between client context and model payload.")
        return continue_resumable_workflow(model_ref or context_ref, state_paths=self.state_paths)

    def _kernel_cancel_active_run(self, invocation: AgentToolInvocation) -> AgentToolResult:
        records = list(self.workflow_run_store.list_active_runs()) if self.workflow_run_store is not None else []
        active_runs = [workflow_run_summary(record) for record in records]
        if not records:
            return ok_result(invocation.tool_name, effect="none", user_visible_summary="No active Kernel workflow run is currently cancellable.", active_state={"cancel_status": "no_active_run", "active_workflow_run_count": 0}, extra={"cancel_status": "no_active_run"})
        if self.state_paths is None or self.workflow_run_store is None:
            return blocked_result(invocation.tool_name, code="kernel_state_unavailable", message="The Kernel requires a resolved state root before it can cancel an active workflow.", active_state={"cancel_status": "kernel_state_unavailable", "active_workflow_runs": active_runs, "active_workflow_run_count": len(active_runs)})
        workflow_run_ids = [str(record.workflow_run_id) for record in records]
        termination = terminate_background_continuations(self.state_paths, workflow_run_ids=workflow_run_ids)
        cancelled, already_gone = self._cancel_records(records)
        return ok_result(
            invocation.tool_name,
            effect="write",
            user_visible_summary="Active Kernel workflow run cancellation was requested and owned background processes were stopped.",
            active_state={"cancel_status": "cancelled", "active_workflow_runs": active_runs, "active_workflow_run_count": len(active_runs), "cancelled_workflow_run_ids": cancelled, "already_inactive_workflow_run_ids": already_gone, "background_process_termination": termination},
            extra={"cancel_status": "cancelled"},
        )

    def _cancel_records(self, records: list[Any]) -> tuple[list[str], list[str]]:
        cancelled: list[str] = []
        already_gone: list[str] = []
        for record in records:
            workflow_run_id = str(record.workflow_run_id)
            append_background_continuation_terminal_progress(self.state_paths, workflow_run_id=workflow_run_id, workflow_tool=str(record.workflow_tool), result_status="cancelled", current_state_summary="user_cancelled")
            try:
                self.workflow_run_store.mark_run_cancelled(workflow_run_id)
            except ResumeStateNotFoundError:
                already_gone.append(workflow_run_id)
            else:
                cancelled.append(workflow_run_id)
        return cancelled, already_gone


def _resume_summary(payload: Mapping[str, Any], resume_options: list[Any], pending_interactions: list[Any]) -> dict[str, Any]:
    workflow_run_id = str(payload["workflow_run_id"])
    return {
        "workflow_ref": opaque_ref(workflow_run_id),
        "workflow_tool": payload.get("paused_function") or payload.get("workflow_tool"),
        "next_expected_transition": payload.get("next_expected_transition"),
        "resume_options": [item.to_dict() for item in resume_options if item.workflow_run_id == workflow_run_id],
        "has_pending_confirmation": bool(payload.get("pending_confirmation_refs")),
        "pending_interaction_count": len(pending_interactions),
        "resume_status": "available",
    }


def _invalid_resume_ref(values: Mapping[str, Any], normalized: str | None) -> bool:
    return "resume_option_ref" in values and not normalized
