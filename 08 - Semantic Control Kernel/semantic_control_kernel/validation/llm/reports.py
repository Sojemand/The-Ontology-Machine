from __future__ import annotations

from semantic_control_kernel.types.llm_calls import LLMFunctionDefinition, LLMValidationReport
from semantic_control_kernel.validation.llm.common import unique


def failed_report(
    definition: LLMFunctionDefinition,
    attempt_index: int,
    *,
    parse_status: str,
    error_codes: tuple[str, ...],
    summary: str,
    paths: tuple[str, ...],
) -> LLMValidationReport:
    return LLMValidationReport(
        llm_function_name=definition.llm_function_name,
        attempt_index=attempt_index,
        attempted_schema=definition.output_contract,
        parse_status=parse_status,
        validation_status="failed",
        error_codes=tuple(unique(error_codes)),
        error_summary=summary,
        blocking_paths=tuple(unique(paths)),
    )
