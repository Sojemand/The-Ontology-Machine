from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.validation.contract_validation import validate_contract


FORBIDDEN_UPDATE_STATE_KEYS = frozenset(
    {
        "coverage_findings",
        "validation",
        "quality",
        "confidence",
        "prompt",
        "prompt_text",
        "raw_provider_response",
        "llm_response",
        "report_seed",
        "user_report_samples_seed",
    }
)


class UpdateStateValidationError(ValueError):
    pass


def validate_update_state_artifact(payload: Mapping[str, Any], expected_schema_version: str) -> None:
    validate_contract(payload, expected_schema_version=expected_schema_version)
    _reject_forbidden_keys(payload)


def _reject_forbidden_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_UPDATE_STATE_KEYS:
                raise UpdateStateValidationError(f"Update-state artifact must not contain {child_path}.")
            _reject_forbidden_keys(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, f"{path}[{index}]")
