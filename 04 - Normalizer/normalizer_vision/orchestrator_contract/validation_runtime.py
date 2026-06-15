"""Runtime settings parsing for orchestrator payloads."""
from __future__ import annotations

from .types import RuntimeSettings


def parse_runtime_settings(payload: dict) -> RuntimeSettings:
    settings = payload.get("runtime_settings")
    if not isinstance(settings, dict):
        raise ValueError("runtime_settings fehlt.")
    model = str(settings.get("model", "")).strip()
    if not model:
        raise ValueError("runtime_settings.model fehlt.")
    max_output_tokens = settings.get("max_output_tokens")
    if isinstance(max_output_tokens, bool):
        raise ValueError("runtime_settings.max_output_tokens muss eine positive Ganzzahl sein.")
    try:
        parsed_max_output_tokens = int(max_output_tokens)
    except (TypeError, ValueError):
        raise ValueError("runtime_settings.max_output_tokens muss eine positive Ganzzahl sein.") from None
    if parsed_max_output_tokens < 1:
        raise ValueError("runtime_settings.max_output_tokens muss eine positive Ganzzahl sein.")
    return RuntimeSettings(model=model, max_output_tokens=parsed_max_output_tokens)
