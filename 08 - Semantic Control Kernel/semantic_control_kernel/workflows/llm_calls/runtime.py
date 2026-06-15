from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from semantic_control_kernel.adapters.llm_adapter import (
    LLMCredentialsMissingError,
    LLMHostCapabilityMissingError,
    LLMInvalidModelProfileError,
    LLMRuntimeMissingError,
)
from semantic_control_kernel.types.llm_calls import LLMRuntimeSettings
from semantic_control_kernel.workflows.llm_calls.output_schemas import schema_supports_strict


RUNTIME_PROFILE_NAME = "semantic_control_kernel_llm"
FIXED_TEMPERATURE = 0.0


def coerce_runtime_settings(value: Mapping[str, Any] | None) -> LLMRuntimeSettings:
    if value is None:
        raise LLMRuntimeMissingError(f"Missing required runtime profile {RUNTIME_PROFILE_NAME}.")
    if not isinstance(value, Mapping) or not isinstance(value.get(RUNTIME_PROFILE_NAME), Mapping):
        raise LLMRuntimeMissingError(f"Missing required runtime profile {RUNTIME_PROFILE_NAME}.")
    value = value[RUNTIME_PROFILE_NAME]
    if value.get("credentials_available") is False:
        raise LLMCredentialsMissingError(f"{RUNTIME_PROFILE_NAME} credentials are not available.")
    if value.get("host_capability_available") is False:
        raise LLMHostCapabilityMissingError(f"{RUNTIME_PROFILE_NAME} host capability is not available.")
    model = value.get("model")
    max_output_tokens = value.get("max_output_tokens")
    if not isinstance(model, str) or not model.strip():
        raise LLMInvalidModelProfileError(f"{RUNTIME_PROFILE_NAME}.model is required.")
    if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
        raise LLMInvalidModelProfileError(f"{RUNTIME_PROFILE_NAME}.max_output_tokens must be a positive integer.")
    timeout_seconds = value.get("timeout_seconds")
    if timeout_seconds is not None and (not isinstance(timeout_seconds, int) or timeout_seconds <= 0):
        raise LLMInvalidModelProfileError(f"{RUNTIME_PROFILE_NAME}.timeout_seconds must be a positive integer.")
    provider_family = value.get("provider_family")
    if provider_family is not None and (not isinstance(provider_family, str) or not provider_family.strip()):
        raise LLMInvalidModelProfileError(f"{RUNTIME_PROFILE_NAME}.provider_family must be a non-empty string.")
    return LLMRuntimeSettings(
        model=model,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        provider_family=provider_family,
    )


def provider_response_mode(call_type: str, target_schema: Mapping[str, Any] | None = None) -> str:
    if call_type == "report_text":
        return "text"
    if schema_supports_strict(target_schema):
        return "json_schema"
    return "json_object"
