from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.adapters.llm_adapter import LLMCallCancelled, LLMFunctionAdapter
from semantic_control_kernel.adapters.orchestrator import OrchestratorAdapter
from semantic_control_kernel.types.llm_calls import CancellationToken, LLMProviderRequest, LLMProviderResponse
from semantic_control_kernel.workflows.llm_calls.runtime import RUNTIME_PROFILE_NAME


class OrchestratorHostedLLMAdapter(LLMFunctionAdapter):
    def __init__(
        self,
        *,
        state_root: str | Path,
        pipeline_root: str | Path | None = None,
        orchestrator_adapter: Any | None = None,
    ) -> None:
        self.orchestrator = orchestrator_adapter or OrchestratorAdapter(
            state_root=state_root,
            pipeline_root=pipeline_root,
        )

    def runtime_profile(self) -> dict[str, Any]:
        try:
            result = self.orchestrator.kernel_llm_runtime_profile({"action": "kernel_llm_runtime_profile"})
        except Exception as exc:
            return {RUNTIME_PROFILE_NAME: _missing_profile(str(exc))}
        payload = _result_payload(result)
        if payload.get("status") != "ok":
            return {RUNTIME_PROFILE_NAME: _missing_profile(_diagnostic_summary(payload))}
        output_refs = payload.get("output_refs")
        settings = output_refs.get("runtime_settings") if isinstance(output_refs, Mapping) else None
        if isinstance(settings, Mapping) and isinstance(settings.get(RUNTIME_PROFILE_NAME), Mapping):
            return {RUNTIME_PROFILE_NAME: dict(settings[RUNTIME_PROFILE_NAME])}
        return {RUNTIME_PROFILE_NAME: _missing_profile("Orchestrator did not return semantic_control_kernel_llm.")}

    def generate(
        self,
        request: LLMProviderRequest,
        cancellation: CancellationToken | None = None,
    ) -> LLMProviderResponse:
        if cancellation is not None and cancellation.is_cancelled:
            raise LLMCallCancelled("LLM call cancelled before provider execution.")
        try:
            result = self.orchestrator.kernel_llm_generate(
                {
                    "action": "kernel_llm_generate",
                    "llm_provider_request": request.to_dict(),
                }
            )
        except Exception as exc:
            return _failure_response("host_capability_missing", request.model, str(exc))
        payload = _result_payload(result)
        if payload.get("status") != "ok":
            return _failure_response("host_capability_missing", request.model, _diagnostic_summary(payload))
        output_refs = payload.get("output_refs")
        llm_response = output_refs.get("llm_response") if isinstance(output_refs, Mapping) else None
        if not isinstance(llm_response, Mapping):
            return _failure_response("provider_error", request.model, "Orchestrator did not return llm_response.")
        return _provider_response_from_mapping(llm_response, fallback_model=request.model)


def _result_payload(result: Any) -> dict[str, Any]:
    if hasattr(result, "to_dict"):
        payload = result.to_dict()
        return dict(payload) if isinstance(payload, Mapping) else {}
    return dict(result) if isinstance(result, Mapping) else {}


def _missing_profile(message: str) -> dict[str, Any]:
    return {
        "model": "",
        "max_output_tokens": 1,
        "credentials_available": True,
        "host_capability_available": False,
        "provider_family": "",
        "message": message,
    }


def _failure_response(status: str, model: str, message: str) -> LLMProviderResponse:
    return LLMProviderResponse(
        provider="orchestrator",
        model=model,
        response_id=f"{status}_from_orchestrator",
        status=status,
        output_text="",
        raw_provider_response_ref={"error_code": status},
        error_code=status,
        error_message=message,
    )


def _provider_response_from_mapping(payload: Mapping[str, Any], *, fallback_model: str) -> LLMProviderResponse:
    raw_ref = payload.get("raw_provider_response_ref")
    usage = payload.get("usage")
    return LLMProviderResponse(
        provider=str(payload.get("provider") or "orchestrator"),
        model=str(payload.get("model") or fallback_model),
        response_id=str(payload.get("response_id") or "orchestrator_llm_response"),
        status=str(payload.get("status") or "provider_error"),
        output_text=str(payload.get("output_text") or ""),
        raw_provider_response_ref=dict(raw_ref) if isinstance(raw_ref, Mapping) else {},
        usage=dict(usage) if isinstance(usage, Mapping) else {},
        finish_reason=str(payload.get("finish_reason")) if payload.get("finish_reason") is not None else None,
        error_code=str(payload.get("error_code")) if payload.get("error_code") is not None else None,
        error_message=str(payload.get("error_message")) if payload.get("error_message") is not None else None,
    )


def _diagnostic_summary(payload: Mapping[str, Any]) -> str:
    diagnostics = payload.get("diagnostics")
    if isinstance(diagnostics, list) and diagnostics:
        first = diagnostics[0]
        if isinstance(first, Mapping):
            return str(first.get("summary") or first.get("message") or first.get("code") or "Orchestrator LLM call failed.")
    return str(payload.get("status") or "Orchestrator LLM call failed.")


__all__ = ["OrchestratorHostedLLMAdapter"]
