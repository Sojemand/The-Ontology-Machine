from __future__ import annotations

import re
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.types.llm_calls import LLMFunctionDefinition, LLMProviderResponse
from semantic_control_kernel.workflows.llm_calls.artifact_redaction import redact_capture_payload

_BINDING_PAYLOAD_KEYS = {
    "{{kernel_sample_analyses_v1_json}}": ("sample_analyses",),
    "{{kernel_taxonomy_projection_authoring_view_v1_json}}": ("taxonomy_authoring_view",),
    "{{user_report_samples_seed_json}}": ("user_report_samples_seed",),
}


def _payload_for_binding(binding: str | None, input_payload: Any) -> Any:
    if binding is None or not isinstance(input_payload, Mapping):
        return input_payload
    for key in _BINDING_PAYLOAD_KEYS.get(binding, ()):
        if key in input_payload:
            return input_payload[key]
    return input_payload


def _response_capture_payload(
    *,
    definition: LLMFunctionDefinition,
    analysis_run_id: str,
    attempt_index: int,
    response: LLMProviderResponse,
    parsed_output: Any,
    parse_status: str,
    validation_status: str,
    validation_errors: list[str],
) -> dict[str, Any]:
    payload = {
        "schema_version": "kernel.llm_response_capture.v1",
        "analysis_run_id": analysis_run_id,
        "llm_function": definition.llm_function_name,
        "created_at": utc_iso(),
        "provider": response.provider,
        "model": response.model,
        "response_id": response.response_id,
        "status": "complete" if response.status == "complete" else "error",
        "raw_provider_response": redact_capture_payload(response.raw_provider_response_ref),
        "output_text": redact_capture_payload(response.output_text),
        "parsed_json": parsed_output if isinstance(parsed_output, Mapping) else {},
        "parse_status": parse_status,
        "validation_status": validation_status,
        "validation_errors": list(validation_errors),
        "attempt_index": attempt_index,
    }
    if response.error_code is not None:
        payload["error_code"] = response.error_code
    if response.error_message is not None:
        payload["error_message"] = response.error_message
    return payload


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", value)
    return cleaned or "sample"
