from __future__ import annotations

from semantic_control_kernel.types.llm_calls import (
    CancellationToken,
    LLMProviderRequest,
    LLMProviderResponse,
)


class LLMAdapterError(RuntimeError):
    error_code = "llm_adapter_error"


class LLMRuntimeMissingError(LLMAdapterError):
    error_code = "llm_runtime_missing"


class LLMCredentialsMissingError(LLMAdapterError):
    error_code = "credentials_missing"


class LLMInvalidModelProfileError(LLMAdapterError):
    error_code = "invalid_model_profile"


class LLMHostCapabilityMissingError(LLMAdapterError):
    error_code = "host_capability_missing"


class LLMCallCancelled(LLMAdapterError):
    error_code = "cancelled"


class LLMFunctionAdapter:
    def generate(
        self,
        request: LLMProviderRequest,
        cancellation: CancellationToken | None = None,
    ) -> LLMProviderResponse:
        if cancellation is not None and cancellation.is_cancelled:
            raise LLMCallCancelled("LLM call cancelled before provider execution.")
        raise LLMRuntimeMissingError(
            "semantic_control_kernel_llm runtime settings are not injected for this Kernel runtime."
        )
