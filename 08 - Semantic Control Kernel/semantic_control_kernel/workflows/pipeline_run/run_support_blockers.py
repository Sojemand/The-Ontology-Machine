from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.policy.batch_policy import is_valid_pipeline_batch_id
from semantic_control_kernel.types.batches import (
    PipelineInputFile,
    PipelineRunBlocker,
    PipelineRunTarget,
    SEMANTIC_RELEASE_ACTIVE,
)


def create_blocker(
    *,
    step_id: str,
    function_or_route: str,
    blocker_code: str,
    summary: str,
    recovery_state_class: str = "support_only_unrecoverable",
    diagnostics: Sequence[Mapping[str, Any]] = (),
    support_bundle_ref: Mapping[str, Any] | None = None,
    resume_descriptor: Mapping[str, Any] | None = None,
) -> PipelineRunBlocker:
    return PipelineRunBlocker(
        blocker_code=blocker_code,
        step_id=step_id,
        function_or_route=function_or_route,
        recovery_state_class=recovery_state_class,
        user_visible_summary=summary,
        diagnostics=tuple(dict(item) for item in diagnostics),
        support_bundle_ref=dict(support_bundle_ref) if support_bundle_ref is not None else None,
        resume_descriptor=dict(resume_descriptor) if resume_descriptor is not None else None,
    )


def _precondition_blocker(
    target: PipelineRunTarget | None,
    input_files: Sequence[PipelineInputFile],
    confirmation: Mapping[str, Any] | None,
    *,
    workflow_tool: str,
) -> PipelineRunBlocker | None:
    if target is None:
        return create_blocker(
            step_id="resolving_target",
            function_or_route=workflow_tool,
            blocker_code="database_missing",
            recovery_state_class="target_identity_changed",
            summary="Pipeline run target is missing from Kernel workflow state.",
        )
    if target.semantic_release_state != SEMANTIC_RELEASE_ACTIVE:
        return create_blocker(
            step_id="resolving_target",
            function_or_route=workflow_tool,
            blocker_code="release_missing" if target.semantic_release_state == "no_semantic_release" else "release_incomplete",
            recovery_state_class="semantic_release_incomplete_staged",
            summary="Pipeline run requires semantic_release_active before owner mutation.",
        )
    return _input_or_binding_blocker(target, input_files, confirmation, workflow_tool=workflow_tool)


def _input_or_binding_blocker(
    target: PipelineRunTarget,
    input_files: Sequence[PipelineInputFile],
    confirmation: Mapping[str, Any] | None,
    *,
    workflow_tool: str,
) -> PipelineRunBlocker | None:
    if not target.has_exact_binding_proof:
        return create_blocker(
            step_id="resolving_target",
            function_or_route=workflow_tool,
            blocker_code="binding_conflict",
            recovery_state_class="broken_database_artifact_binding",
            summary="Pipeline run requires exact DatabaseArtifactBindingRegistry proof.",
        )
    if not input_files:
        return create_blocker(
            step_id="resolving_target",
            function_or_route=workflow_tool,
            blocker_code="input_missing",
            recovery_state_class="expired_pending_interaction",
            summary="Pipeline run requires Input-file evidence before owner mutation.",
        )
    if not isinstance(confirmation, Mapping) or confirmation.get("status") not in {"confirmed", "submitted", True}:
        return create_blocker(
            step_id="awaiting_confirmation",
            function_or_route=workflow_tool,
            blocker_code="input_missing",
            recovery_state_class="expired_pending_interaction",
            summary="Input-file presence must be confirmed through Kernel/UI state.",
        )
    return None


def _resume_preflight_blocker(
    target: PipelineRunTarget | None,
    resume_state: Mapping[str, Any] | None,
) -> PipelineRunBlocker | None:
    if not isinstance(resume_state, Mapping) or not resume_state.get("owner_run_completed"):
        return None
    if not resume_state.get("correlation_pending") or target is None:
        return None
    if dict(resume_state.get("target_identity") or {}) != target.target_identity:
        return create_blocker(
            step_id="resume_preflight",
            function_or_route="pipeline_run",
            blocker_code="target_identity_changed",
            recovery_state_class="target_identity_changed",
            summary="Resume state target identity does not match the current Kernel target.",
        )
    return _resume_manifest_blocker(resume_state)


def _resume_manifest_blocker(resume_state: Mapping[str, Any]) -> PipelineRunBlocker | None:
    pipeline_batch_id = str(resume_state.get("pipeline_batch_id") or "")
    if not is_valid_pipeline_batch_id(pipeline_batch_id):
        return create_blocker(
            step_id="resume_preflight",
            function_or_route="pipeline_run",
            blocker_code="partial_pipeline_run",
            recovery_state_class="partial_pipeline_run",
            summary="Resume state is missing a valid Kernel-issued pipeline_batch_id.",
        )
    owner_result = resume_state.get("owner_adapter_result")
    if not isinstance(owner_result, Mapping) or owner_result.get("status") != "ok":
        return create_blocker(
            step_id="resume_preflight",
            function_or_route="pipeline_run",
            blocker_code="partial_pipeline_run",
            recovery_state_class="partial_pipeline_run",
            summary="Resume state is missing an ok owner adapter receipt.",
        )
    return None
