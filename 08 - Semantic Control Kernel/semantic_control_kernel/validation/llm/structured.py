from __future__ import annotations

import json
from typing import Any, Mapping

from semantic_control_kernel.types.llm_calls import LLMFunctionDefinition, LLMValidationReport
from semantic_control_kernel.validation.contract_validation import (
    EnumValidationError,
    KernelContractError,
    MissingRequiredFieldError,
    SchemaVersionMismatchError,
    UnknownFieldError,
    validate_contract,
)
from semantic_control_kernel.validation.llm.canonicalization import canonicalize_structured_output
from semantic_control_kernel.validation.llm.context import LLMValidationContext, derive_validation_context
from semantic_control_kernel.validation.llm.common import unique
from semantic_control_kernel.validation.llm.reports import failed_report
from semantic_control_kernel.validation.llm.schema import target_schema_errors
from semantic_control_kernel.validation.llm.semantic_rules import context_mismatch_errors, function_specific_errors
from semantic_control_kernel.workflows.llm_calls.output_schemas import build_output_schema


def validate_structured_output_text(
    *,
    output_text: str,
    definition: LLMFunctionDefinition,
    context: LLMValidationContext | None = None,
    attempt_index: int = 1,
) -> tuple[dict[str, Any] | None, LLMValidationReport]:
    parsed, parse_report = parse_strict_json_object(output_text, definition, attempt_index)
    if parsed is None:
        return None, parse_report
    context = context or derive_validation_context(definition, None)
    parsed = canonicalize_structured_output(parsed, definition=definition, context=context)
    report = validate_structured_output(
        parsed,
        definition=definition,
        context=context,
        attempt_index=attempt_index,
    )
    return parsed, report


def parse_strict_json_object(
    output_text: str,
    definition: LLMFunctionDefinition,
    attempt_index: int = 1,
) -> tuple[dict[str, Any] | None, LLMValidationReport]:
    text = output_text.strip()
    if not text:
        return None, failed_report(
            definition,
            attempt_index,
            parse_status="missing_output",
            error_codes=("invalid_json",),
            summary="Provider output was empty.",
            paths=("$",),
        )
    if text.startswith("```"):
        return None, failed_report(
            definition,
            attempt_index,
            parse_status="invalid_json",
            error_codes=("markdown_outside_json",),
            summary="Provider output must be exactly one JSON object with no Markdown or explanatory text.",
            paths=("$",),
        )
    if not text.startswith("{"):
        return None, failed_report(
            definition,
            attempt_index,
            parse_status="invalid_json",
            error_codes=("invalid_json",),
            summary="Provider output must be exactly one JSON object.",
            paths=("$",),
        )
    decoder = json.JSONDecoder()
    try:
        parsed, end_index = decoder.raw_decode(text)
    except json.JSONDecodeError as exc:
        return None, failed_report(
            definition,
            attempt_index,
            parse_status="invalid_json",
            error_codes=("invalid_json",),
            summary=exc.msg,
            paths=(f"${exc.pos}",),
        )
    if text[end_index:].strip():
        return None, failed_report(
            definition,
            attempt_index,
            parse_status="invalid_json",
            error_codes=("markdown_outside_json",),
            summary="Provider output contains text outside the JSON object.",
            paths=("$",),
        )
    if not isinstance(parsed, dict):
        status = "not_json_array" if isinstance(parsed, list) else "not_json_object"
        return None, failed_report(
            definition,
            attempt_index,
            parse_status=status,
            error_codes=("invalid_json",),
            summary="Provider output must be one JSON object.",
            paths=("$",),
        )
    return parsed, LLMValidationReport(
        llm_function_name=definition.llm_function_name,
        attempt_index=attempt_index,
        attempted_schema=definition.output_contract,
        parse_status="valid_json",
        validation_status="not_run",
        error_codes=(),
        error_summary="JSON parsed.",
        blocking_paths=(),
    )


def validate_structured_output(
    payload: Mapping[str, Any],
    *,
    definition: LLMFunctionDefinition,
    context: LLMValidationContext | None = None,
    attempt_index: int = 1,
) -> LLMValidationReport:
    context = context or LLMValidationContext()
    errors: list[tuple[str, str, str]] = []
    copied = canonicalize_structured_output(payload, definition=definition, context=context)
    try:
        validate_contract(copied, expected_schema_version=definition.output_contract)
    except SchemaVersionMismatchError as exc:
        errors.append(("schema_version_mismatch", str(exc), "$.schema_version"))
    except MissingRequiredFieldError as exc:
        errors.append(("missing_required_fields", str(exc), "$"))
    except UnknownFieldError as exc:
        errors.append(("unknown_fields", str(exc), "$"))
    except EnumValidationError as exc:
        errors.append(("enum_mismatch", str(exc), "$"))
    except KernelContractError as exc:
        errors.append(("function_rule_violation", str(exc), "$"))

    target_schema = build_output_schema(definition, context.input_payload)
    if target_schema is not None:
        errors.extend(target_schema_errors(copied, target_schema))
    errors.extend(context_mismatch_errors(copied, context))
    errors.extend(function_specific_errors(definition.llm_function_name, copied, context))
    if errors:
        return failed_report(
            definition,
            attempt_index,
            parse_status="valid_json",
            error_codes=tuple(unique(code for code, _, _ in errors)),
            summary="; ".join(unique(message for _, message, _ in errors)),
            paths=tuple(unique(path for _, _, path in errors)),
        )
    return LLMValidationReport(
        llm_function_name=definition.llm_function_name,
        attempt_index=attempt_index,
        attempted_schema=definition.output_contract,
        parse_status="valid_json",
        validation_status="passed",
        error_codes=(),
        error_summary="Validation passed.",
        blocking_paths=(),
    )
