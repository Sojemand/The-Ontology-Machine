"""LLM-backed OCR port that preserves the legacy Optimizer OCR payload."""
from __future__ import annotations

from pathlib import Path
import time
from typing import Any

from .assets import load_image_assets
from .errors import LlmOcrConfigurationError, LlmOcrError, LlmOcrResponseError
from .prompting import DEFAULT_OCR_PROMPT_TEMPLATE, PROMPT_FILE_NAME
from . import provider as _provider
from .response_payload import (
    envelope as _envelope,
    metadata as _metadata,
    normalize_blocks as _normalize_blocks,
    parse_model_json as _parse_model_json,
)
from .settings import LlmOcrSettings, settings_from_env

_post_json = _provider._post_json
_request_oauth_backend = _provider._request_oauth_backend


def extract_page_assets(
    image_paths: list[str],
    *,
    source_path: str | Path | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """Run LLM-OCR for rendered page/image assets and return the legacy OCR payload."""
    start = time.perf_counter_ns()
    try:
        settings = settings_from_env(timeout_seconds=timeout_seconds)
        assets = load_image_assets(image_paths)
        response_text = _provider.call_llm_ocr(
            settings,
            assets,
            source_path=source_path,
            post_json=_post_json,
            request_oauth_backend=_request_oauth_backend,
        )
        model_payload = _parse_model_json(response_text)
        blocks = _normalize_blocks(model_payload.get("blocks"))
        metadata = _metadata(settings, assets, model_payload.get("metadata"), blocks)
        return _envelope("success", blocks, metadata, [], start)
    except LlmOcrError as exc:
        return _envelope("error", [], {"ocr_backend": "llm", "ocr_engine": "llm"}, [str(exc)], start)
    except OSError as exc:
        return _envelope("error", [], {"ocr_backend": "llm", "ocr_engine": "llm"}, [f"LLM-OCR Page-Asset konnte nicht gelesen werden: {exc}"], start)


def check_readiness() -> tuple[bool, str]:
    """Check optimizer_ocr configuration without persisting or exposing secrets."""
    try:
        settings = settings_from_env()
    except LlmOcrConfigurationError as exc:
        return False, str(exc)
    return True, f"optimizer_ocr bereit ({settings.provider_id}, {settings.provider_family}, model={settings.model})"


__all__ = [
    "DEFAULT_OCR_PROMPT_TEMPLATE",
    "LlmOcrConfigurationError",
    "LlmOcrError",
    "LlmOcrResponseError",
    "LlmOcrSettings",
    "PROMPT_FILE_NAME",
    "check_readiness",
    "extract_page_assets",
]
