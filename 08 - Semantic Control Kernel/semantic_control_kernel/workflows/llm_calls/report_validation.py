from __future__ import annotations

import json
import re

from semantic_control_kernel.types.llm_calls import LLMFunctionDefinition, LLMValidationReport


REPORT_HEADINGS: dict[str, tuple[str, ...]] = {
    "user_report_samples": (
        "# Sample Analysis Report",
        "## 1. Overview",
        "## 2. What The Samples Show",
        "## 3. Taxonomy Perspective",
        "## 4. Projection Perspective",
        "## 5. Important Findings",
        "## 6. Points To Review",
    ),
}

_IMPLEMENTATION_TERMS = (
    "schema_version",
    "downstream consumer",
    "pipeline mechanics",
    "implementation detail",
    "internal function",
    "schema version",
    "llm function",
    "analyze_samples",
    "user_report_samples",
    "create_taxonomy_to_sample_analyses",
    "create_projections_to_sample_analyses",
)
_SCHEMA_VERSION_RE = re.compile(r"\bkernel\.[a-z0-9_.]+\.v1\b|\bplain_markdown\.[a-z0-9_.]+\.v1\b", re.IGNORECASE)
_MUTATION_CLAIMS = re.compile(
    r"\b(taxonomy|projection|semantic release|database)\s+(was|were|has been|will be|is)\s+"
    r"(created|changed|updated|modified|validated|activated|deleted|removed)\b",
    re.IGNORECASE,
)


def validate_report_output(
    *,
    report_text: str,
    definition: LLMFunctionDefinition,
    attempt_index: int = 1,
) -> LLMValidationReport:
    errors: list[tuple[str, str]] = []
    stripped = normalize_report_output(report_text).strip()
    if _looks_like_json(stripped):
        errors.append(("function_rule_violation", "Report output must be Markdown/plain text, not JSON."))
    if stripped.startswith("---") or "\n---\n" in stripped:
        errors.append(("function_rule_violation", "Report output must not include metadata blocks."))
    headings = REPORT_HEADINGS[definition.llm_function_name]
    actual_headings = tuple(line.strip() for line in stripped.splitlines() if line.strip().startswith("#"))
    if actual_headings != headings:
        errors.append(("function_rule_violation", "Report headings are missing, renamed or reordered."))
    lower = stripped.lower()
    for term in _IMPLEMENTATION_TERMS:
        if term in lower:
            errors.append(("function_rule_violation", f"Report contains implementation vocabulary: {term}."))
            break
    if _SCHEMA_VERSION_RE.search(stripped):
        errors.append(("function_rule_violation", "Report contains internal schema version vocabulary."))
    if _MUTATION_CLAIMS.search(stripped):
        errors.append(("function_rule_violation", "Report must not claim taxonomy, projection or release mutation."))
    if errors:
        return LLMValidationReport(
            llm_function_name=definition.llm_function_name,
            attempt_index=attempt_index,
            attempted_schema=definition.output_contract,
            parse_status="not_json_object",
            validation_status="failed",
            error_codes=tuple(code for code, _ in errors),
            error_summary="; ".join(message for _, message in errors),
            blocking_paths=("$",),
        )
    return LLMValidationReport(
        llm_function_name=definition.llm_function_name,
        attempt_index=attempt_index,
        attempted_schema=definition.output_contract,
        parse_status="not_json_object",
        validation_status="passed",
        error_codes=(),
        error_summary="Report validation passed.",
        blocking_paths=(),
    )


def normalize_report_output(report_text: str) -> str:
    stripped = str(report_text or "").strip()
    if not _looks_like_json(stripped):
        return report_text
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return report_text
    if isinstance(parsed, dict):
        for key in ("report", "markdown", "content", "text"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return report_text


def _looks_like_json(value: str) -> bool:
    if not value or value[0] not in "{[":
        return False
    try:
        json.loads(value)
    except json.JSONDecodeError:
        return False
    return True
