from __future__ import annotations

from pathlib import Path
from typing import Any

from .prompting import chat_content_parts, responses_content_parts
from .settings import LlmOcrSettings


def responses_payload(settings: LlmOcrSettings, assets: list[dict[str, str]], *, source_path: str | Path | None) -> dict[str, Any]:
    return {
        "model": settings.model,
        "input": [{"role": "user", "content": responses_content_parts(assets, source_path=source_path)}],
        "max_output_tokens": settings.max_output_tokens,
        "text": {"format": {"type": "json_object"}},
    }


def chat_payload(settings: LlmOcrSettings, assets: list[dict[str, str]], *, source_path: str | Path | None) -> dict[str, Any]:
    return {
        "model": settings.model,
        "messages": [{"role": "user", "content": chat_content_parts(assets, source_path=source_path)}],
        "max_tokens": settings.max_output_tokens,
        "response_format": {"type": "json_object"},
    }
