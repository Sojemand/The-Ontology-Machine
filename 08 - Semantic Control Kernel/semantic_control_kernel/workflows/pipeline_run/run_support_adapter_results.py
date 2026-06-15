from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker
from semantic_control_kernel.types.batches import PipelineRunBlocker
from semantic_control_kernel.workflows.pipeline_run.run_support_blockers import create_blocker


JsonObject = dict[str, Any]


def _adapter_output(result: object) -> JsonObject:
    if isinstance(result, AdapterCallResult):
        output = result.to_dict().get("output_refs")
        return dict(output) if isinstance(output, Mapping) else {}
    if isinstance(result, Mapping):
        return dict(result)
    return {}


def _adapter_ref(result: object) -> Mapping[str, Any]:
    if isinstance(result, AdapterCallResult):
        payload = result.to_dict()
        return {
            "adapter_call_id": payload.get("adapter_call_id", ""),
            "adapter_name": payload.get("adapter_name", ""),
            "status": payload.get("status", ""),
        }
    if isinstance(result, MissingCapabilityBlocker):
        return result.to_dict()
    if isinstance(result, Mapping):
        return dict(result)
    return {}


def _blocker_from_adapter_result(
    step_id: str,
    result: object,
    *,
    before_owner_mutation: bool,
) -> PipelineRunBlocker | None:
    if isinstance(result, PipelineRunBlocker):
        return result
    if isinstance(result, MissingCapabilityBlocker):
        return _missing_capability_blocker(step_id, result, before_owner_mutation=before_owner_mutation)
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        return _adapter_call_blocker(step_id, result, before_owner_mutation=before_owner_mutation)
    if result is None:
        return create_blocker(
            step_id=step_id,
            function_or_route=step_id,
            blocker_code="invalid_owner_response",
            recovery_state_class="support_only_unrecoverable",
            summary="Pipeline adapter returned no result.",
        )
    return None


def adapter_failure_summary(result: AdapterCallResult) -> str:
    payload = result.to_dict()
    status = str(payload.get("status") or result.status)
    detail = _first_adapter_diagnostic_text(payload.get("diagnostics"))
    if detail:
        return f"Pipeline adapter returned {status}: {detail}"
    return f"Pipeline adapter returned {status}."


def _missing_capability_blocker(step_id: str, result: MissingCapabilityBlocker, *, before_owner_mutation: bool) -> PipelineRunBlocker:
    payload = result.to_dict()
    return create_blocker(
        step_id=step_id,
        function_or_route=str(payload.get("kernel_function", step_id)),
        blocker_code="pipeline_capability_missing",
        recovery_state_class="support_only_unrecoverable" if before_owner_mutation else "partial_pipeline_run",
        summary=str(payload.get("blocking_reason", "Required Pipeline capability is not available.")),
        diagnostics=payload.get("diagnostics", ()),
    )


def _adapter_call_blocker(step_id: str, result: AdapterCallResult, *, before_owner_mutation: bool) -> PipelineRunBlocker:
    return create_blocker(
        step_id=step_id,
        function_or_route=str(result.to_dict().get("kernel_function", step_id)),
        blocker_code="partial_pipeline_run" if not before_owner_mutation else str(result.status),
        recovery_state_class="partial_pipeline_run" if not before_owner_mutation else "support_only_unrecoverable",
        summary=adapter_failure_summary(result),
        diagnostics=result.to_dict().get("diagnostics", ()),
    )


def _first_adapter_diagnostic_text(diagnostics: object) -> str:
    if not isinstance(diagnostics, Sequence) or isinstance(diagnostics, (str, bytes, bytearray)):
        return ""
    for item in diagnostics:
        if not isinstance(item, Mapping):
            continue
        for key in ("summary", "safe_summary", "message", "reason"):
            value = str(item.get(key) or "").strip()
            if value:
                return _trim_diagnostic_text(value)
    return ""


def _trim_diagnostic_text(value: str, limit: int = 700) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
