from __future__ import annotations

from typing import Any

from semantic_control_kernel.adapters.llm_adapter import (
    LLMAdapterError,
    LLMCallCancelled,
    LLMFunctionAdapter,
    LLMRuntimeMissingError,
)
from semantic_control_kernel.types.llm_calls import CancellationToken, LLMProviderRequest, LLMProviderResponse


def build_provider_request(
    *,
    definition: Any,
    analysis_run_id: str,
    attempt_index: int,
    settings: Any,
    rendered: Any,
) -> LLMProviderRequest:
    return LLMProviderRequest(
        llm_function_name=definition.llm_function_name,
        analysis_run_id=analysis_run_id,
        attempt_index=attempt_index,
        model=settings.model,
        max_output_tokens=settings.max_output_tokens,
        response_mode=rendered.snapshot["model_request"]["response_format"],
        messages=tuple(rendered.messages),
        target_schema_ref=definition.output_contract,
        timeout_seconds=settings.timeout_seconds,
        provider_family=settings.provider_family,
        target_schema=rendered.output_schema,
        target_schema_name=rendered.output_schema_name,
        target_schema_sha256=rendered.snapshot["model_request"].get("target_schema_sha256"),
    )


def generate_provider_response(
    provider_adapter: LLMFunctionAdapter,
    request: LLMProviderRequest,
    cancellation: CancellationToken | None,
    *,
    settings: Any,
    attempt_index: int,
) -> LLMProviderResponse:
    try:
        return provider_adapter.generate(request, cancellation)
    except LLMCallCancelled:
        raise
    except LLMRuntimeMissingError:
        raise
    except LLMAdapterError as exc:
        return LLMProviderResponse(
            provider="host",
            model=settings.model,
            response_id=f"provider_error_{attempt_index}",
            status=getattr(exc, "error_code", "provider_error"),
            output_text="",
            raw_provider_response_ref={"error_code": getattr(exc, "error_code", "provider_error")},
            error_code=getattr(exc, "error_code", "provider_error"),
            error_message=str(exc),
        )
