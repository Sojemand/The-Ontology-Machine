from __future__ import annotations

import hashlib
import json
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.atomic_json import stable_json_dumps
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.types.llm_calls import LLMFunctionDefinition, LLMRuntimeSettings
from semantic_control_kernel.workflows.llm_calls.output_schemas import build_output_schema, output_schema_name
from semantic_control_kernel.workflows.llm_calls.prompt_templates import OUTPUT_APPENDICES, USER_PROMPT_TEMPLATES
from semantic_control_kernel.workflows.llm_calls.runtime import FIXED_TEMPERATURE, provider_response_mode


_ABSOLUTE_WINDOWS_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_SECRET_KEY_RE = re.compile(r"(api[_-]?key|authorization|bearer|token|secret|credential|password)", re.IGNORECASE)


SYSTEM_PROMPTS: dict[str, str] = {
    "analyze_samples": "",
    "user_report_samples": "",
    "create_taxonomy_to_sample_analyses": "",
    "create_projections_to_sample_analyses": "",
}


@dataclass(frozen=True)
class RenderedPrompt:
    messages: tuple[Mapping[str, str], ...]
    snapshot: dict[str, Any]
    input_hash: str
    output_schema: dict[str, Any] | None = None
    output_schema_name: str | None = None


def render_prompt(
    *,
    definition: LLMFunctionDefinition,
    analysis_run_id: str,
    runtime_settings: LLMRuntimeSettings,
    input_payload: Any,
    binding_artifacts: Mapping[str, str],
    validation_feedback: str | None = None,
) -> RenderedPrompt:
    sanitized_input = redact_prompt_payload(input_payload)
    rendered_input = json.dumps(sanitized_input, indent=2, sort_keys=True)
    feedback_text = ""
    if validation_feedback:
        feedback_text = (
            "\n\nRetry repair rules:\n"
            "- Repair only the same task.\n"
            "- Do not change target, schema, source refs, workflow target, or evidence.\n"
            "- Do not relax required fields or invent best-effort JSON repairs.\n"
            f"- Validation feedback from the previous attempt: {validation_feedback}"
        )
    output_schema = build_output_schema(definition, sanitized_input)
    schema_name = output_schema_name(definition) if output_schema is not None else None
    user_prompt = USER_PROMPT_TEMPLATES[definition.llm_function_name]
    for token, replacement in (
        ("{input_contract}", definition.input_contract),
        ("{output_contract}", definition.output_contract),
        ("{input_json}", rendered_input),
        ("{validation_feedback_block}", feedback_text),
    ):
        user_prompt = user_prompt.replace(token, replacement)
    appendix = OUTPUT_APPENDICES.get(definition.llm_function_name)
    if appendix:
        user_prompt = f"{user_prompt}\n\n{appendix}"
    if output_schema is not None:
        user_prompt = (
            f"{user_prompt}\n\n"
            "Strict OpenAI schema rules:\n"
            "- Follow the attached structured output schema exactly.\n"
            "- Unknown fields are invalid.\n"
            "- Every schema-declared field must be present.\n"
            "- Use null for nullable fields that do not apply, [] for empty arrays, and {} only where the schema explicitly declares an object.\n"
            "- Dynamic marker maps are represented as lists of {domain_id, markers} entries in model output."
        )
    messages = (
        {"role": "system", "content": SYSTEM_PROMPTS[definition.llm_function_name]},
        {"role": "user", "content": user_prompt},
    )
    response_format = provider_response_mode(definition.call_type, output_schema)
    input_hash = _hash_json(sanitized_input)
    model_request: dict[str, Any] = {
        "model": runtime_settings.model,
        "temperature": FIXED_TEMPERATURE,
        "response_format": response_format,
        "max_output_tokens": runtime_settings.max_output_tokens,
        "target_schema_ref": definition.output_contract,
    }
    if output_schema is not None:
        model_request.update(
            {
                "response_format_name": schema_name,
                "response_format_strict": response_format == "json_schema",
                "target_schema_sha256": f"sha256:{_hash_json(output_schema)}",
                "target_schema": output_schema,
            }
        )
    snapshot = {
        "schema_version": "kernel.llm_prompt_snapshot.v1",
        "analysis_run_id": analysis_run_id,
        "llm_function": definition.llm_function_name,
        "created_at": utc_iso(),
        "model_request": model_request,
        "prompt": {
            "system": messages[0]["content"],
            "user": messages[1]["content"],
        },
        "bindings": _binding_metadata(definition, sanitized_input, binding_artifacts),
    }
    return RenderedPrompt(
        messages=messages,
        snapshot=snapshot,
        input_hash=input_hash,
        output_schema=output_schema,
        output_schema_name=schema_name,
    )


def redact_prompt_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            if _SECRET_KEY_RE.search(key_text):
                redacted[key_text] = "[REDACTED]"
            else:
                redacted[key_text] = redact_prompt_payload(child)
        return redacted
    if isinstance(value, list):
        return [redact_prompt_payload(item) for item in value]
    if isinstance(value, str):
        return _sanitize_path_or_secret(value)
    return deepcopy(value)


def _binding_metadata(
    definition: LLMFunctionDefinition,
    input_payload: Any,
    binding_artifacts: Mapping[str, str],
) -> list[dict[str, Any]]:
    sha = _hash_json(input_payload)
    bindings = []
    for name in definition.prompt_bindings:
        artifact_path = binding_artifacts.get(name, _default_binding_path(definition))
        bindings.append(
            {
                "name": name,
                "schema_version": definition.input_contract,
                "artifact_path": artifact_path,
                "sha256": f"sha256:{sha}",
            }
        )
    return bindings


def _default_binding_path(definition: LLMFunctionDefinition) -> str:
    if definition.input_artifact_paths:
        return definition.input_artifact_paths[0].replace("{sample_id}", "<sample_id>")
    return definition.run_folder_template + "/input.json"


def _hash_json(value: Any) -> str:
    return hashlib.sha256(stable_json_dumps({"value": value}).encode("utf-8")).hexdigest()


def _sanitize_path_or_secret(value: str) -> str:
    if _SECRET_KEY_RE.search(value):
        return "[REDACTED]"
    normalized = value.replace("\\", "/")
    if _ABSOLUTE_WINDOWS_RE.match(value) or (os.name != "nt" and value.startswith("/")):
        return f"artifact_ref:{Path(normalized).name}"
    return value
