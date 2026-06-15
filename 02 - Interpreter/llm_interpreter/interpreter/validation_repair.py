"""Repair helpers for targeted post-validation retries."""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from ..models.types import InterpreterConfig
from ..providers import LLMProvider
from . import policy_response
from .types import ProviderCall

logger = logging.getLogger(__name__)


def repair_validation_failure(
    provider: LLMProvider,
    config: InterpreterConfig,
    label: str,
    llm_result: dict[str, Any],
    validation_error: Exception,
    run_provider_call: Callable[[LLMProvider, list[dict[str, Any]], InterpreterConfig, str], ProviderCall],
) -> tuple[dict[str, Any], ProviderCall]:
    logger.warning("[%s] Modell-Output ungueltig, starte gezielten Repair-Retry: %s", label, validation_error)
    repair_messages = _build_validation_repair_messages(llm_result, validation_error)
    repair_call = run_provider_call(provider, repair_messages, config, f"{label}:repair")
    repaired = policy_response.parse_llm_response(repair_call.response_text)
    return repaired, repair_call


def _build_validation_repair_messages(
    llm_result: dict[str, Any],
    validation_error: Exception,
) -> list[dict[str, Any]]:
    previous_json = json.dumps(llm_result, ensure_ascii=False, indent=2)
    user_lines = [
        "The previous JSON response was invalid.",
        f"Validation error: {validation_error}",
        "Repair the JSON so it satisfies the required schema exactly.",
        "Keep all valid content unchanged.",
        "Do not add prose or markdown.",
    ]
    user_lines.extend(["", "Previous JSON:", "```json", previous_json, "```"])
    return [
        {
            "role": "system",
            "content": "Return valid JSON only. Repair the provided JSON to satisfy the schema exactly. Do not add prose.",
        },
        {
            "role": "user",
            "content": "\n".join(user_lines),
        },
    ]
