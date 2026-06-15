from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from semantic_control_kernel.types.llm_call_common import JsonObject, _copy_mapping


@dataclass(frozen=True)
class LLMFunctionDefinition:
    llm_function_name: str
    call_type: str
    input_contract: str
    output_contract: str
    run_folder_template: str
    canonical_output_path: str
    prompt_template_ref: str
    validator_ref: str
    retry_policy_ref: str
    downstream_consumers: tuple[str, ...]
    prompt_bindings: tuple[str, ...]
    input_artifact_paths: tuple[str, ...] = ()

    SCHEMA_VERSION = "kernel.llm_function_definition.v1"

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "llm_function_name": self.llm_function_name,
            "call_type": self.call_type,
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "run_folder_template": self.run_folder_template,
            "canonical_output_path": self.canonical_output_path,
            "prompt_template_ref": self.prompt_template_ref,
            "validator_ref": self.validator_ref,
            "retry_policy_ref": self.retry_policy_ref,
            "downstream_consumers": list(self.downstream_consumers),
            "prompt_bindings": list(self.prompt_bindings),
            "input_artifact_paths": list(self.input_artifact_paths),
        }


@dataclass(frozen=True)
class LLMRuntimeSettings:
    model: str
    max_output_tokens: int
    timeout_seconds: int | None = None
    provider_family: str | None = None

    def to_dict(self) -> JsonObject:
        payload: JsonObject = {
            "model": self.model,
            "max_output_tokens": self.max_output_tokens,
        }
        if self.timeout_seconds is not None:
            payload["timeout_seconds"] = self.timeout_seconds
        if self.provider_family is not None:
            payload["provider_family"] = self.provider_family
        return payload


@dataclass(frozen=True)
class LLMProviderRequest:
    llm_function_name: str
    analysis_run_id: str
    attempt_index: int
    model: str
    max_output_tokens: int
    response_mode: str
    messages: tuple[Mapping[str, str], ...]
    target_schema_ref: str
    timeout_seconds: int | None = None
    provider_family: str | None = None
    target_schema: Mapping[str, Any] | None = None
    target_schema_name: str | None = None
    target_schema_sha256: str | None = None

    SCHEMA_VERSION = "kernel.llm_provider_request.v1"

    def to_dict(self) -> JsonObject:
        payload: JsonObject = {
            "schema_version": self.SCHEMA_VERSION,
            "llm_function_name": self.llm_function_name,
            "analysis_run_id": self.analysis_run_id,
            "attempt_index": self.attempt_index,
            "model": self.model,
            "max_output_tokens": self.max_output_tokens,
            "response_mode": self.response_mode,
            "messages": [dict(message) for message in self.messages],
            "target_schema_ref": self.target_schema_ref,
            "timeout_seconds": self.timeout_seconds,
        }
        if self.provider_family is not None:
            payload["provider_family"] = self.provider_family
        if self.target_schema is not None:
            payload["target_schema"] = _copy_mapping(self.target_schema)
        if self.target_schema_name is not None:
            payload["target_schema_name"] = self.target_schema_name
        if self.target_schema_sha256 is not None:
            payload["target_schema_sha256"] = self.target_schema_sha256
        return payload


@dataclass(frozen=True)
class LLMProviderResponse:
    provider: str
    model: str
    response_id: str
    status: str
    output_text: str
    raw_provider_response_ref: Mapping[str, Any] = field(default_factory=dict)
    usage: Mapping[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    SCHEMA_VERSION = "kernel.llm_provider_response.v1"

    def to_dict(self) -> JsonObject:
        payload: JsonObject = {
            "schema_version": self.SCHEMA_VERSION,
            "provider": self.provider,
            "model": self.model,
            "response_id": self.response_id,
            "status": self.status,
            "output_text": self.output_text,
            "raw_provider_response_ref": _copy_mapping(self.raw_provider_response_ref),
            "usage": _copy_mapping(self.usage),
            "finish_reason": self.finish_reason,
        }
        if self.error_code is not None:
            payload["error_code"] = self.error_code
        if self.error_message is not None:
            payload["error_message"] = self.error_message
        return payload
