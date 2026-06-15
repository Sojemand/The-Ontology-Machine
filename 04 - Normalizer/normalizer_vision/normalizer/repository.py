"""Persistence helpers for normalized outputs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models.serialization import atomic_json_write, utc_now_iso
from ..models.config import NormalizerExecutionConfig


def write_normalized_output(
    *,
    normalized_output_path: Path,
    normalized: dict[str, Any],
) -> Path:
    atomic_json_write(normalized_output_path, normalized)
    return normalized_output_path


def write_normalizer_request(
    *,
    request_output_path: Path,
    structured_path: Path,
    config: NormalizerExecutionConfig,
    provider_name: str,
    projection_selection: dict[str, Any],
    messages: list[dict[str, Any]],
    schema: dict[str, Any] | None,
) -> Path:
    atomic_json_write(
        request_output_path,
        {
            "schema_version": "normalizer.request.v1",
            "captured_at": utc_now_iso(),
            "structured_path": str(structured_path),
            "provider": provider_name,
            "model": config.model,
            "max_output_tokens": config.max_output_tokens,
            "structured_outputs": bool(config.structured_outputs),
            "thinking_effort": config.api_thinking_effort,
            "projection_hint_mode": config.projection_hint_mode,
            "projection_selection": projection_selection,
            "messages": messages,
            "response_schema": schema,
        },
    )
    return request_output_path
