from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.validation.recovery_validation import RECOVERY_OPTION_REQUIRED_FIELDS


def safe_recovery_option(option: Mapping[str, Any]) -> dict[str, Any]:
    safe = safe_payload(dict(option))
    if not isinstance(safe, dict):
        return {}
    return {field_name: safe[field_name] for field_name in RECOVERY_OPTION_REQUIRED_FIELDS if field_name in safe}


def safe_payload(value: Any) -> Any:
    blocked_keys = {"raw_stack_trace", "secret", "secrets", "raw_provider_response", "raw_llm_response", "prompt"}
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            if key_text.casefold() in blocked_keys:
                continue
            cleaned[key_text] = safe_payload(child)
        return cleaned
    if isinstance(value, list):
        return [safe_payload(item) for item in value]
    if isinstance(value, tuple):
        return [safe_payload(item) for item in value]
    if isinstance(value, str):
        return safe_support_text(value)
    return value


def safe_support_text(value: str) -> str:
    blocked_markers = (
        "traceback",
        "raw_stack_trace",
        "raw_provider_response",
        "raw_llm_response",
        "api_key",
        "secret",
        "sk-",
        "prompt:",
    )
    safe_lines = []
    for line in str(value).splitlines() or [""]:
        lowered = line.casefold()
        if any(marker in lowered for marker in blocked_markers):
            continue
        safe_lines.append(line)
    return "\n".join(safe_lines).strip() or "A safe support summary is available in the support bundle."
