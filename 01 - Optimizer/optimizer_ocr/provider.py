"""Provider dispatch for Optimizer OCR."""

from __future__ import annotations

from pathlib import Path

from .errors import LlmOcrConfigurationError
from .provider_extract import extract_chat_text, extract_responses_text
from .provider_http import post_json
from .provider_oauth import call_oauth_backend, request_oauth_backend_default
from .provider_payloads import chat_payload, responses_payload
from .request_capture import persist_request
from .settings import CHAT_FAMILIES, RESPONSES_FAMILIES, LlmOcrSettings


def call_llm_ocr(
    settings: LlmOcrSettings,
    assets: list[dict[str, str]],
    *,
    source_path: str | Path | None,
    post_json=None,
    request_oauth_backend=None,
) -> str:
    post = post_json or post_json_default
    if settings.auth_mode == "oauth":
        return call_oauth_backend(
            settings,
            assets,
            source_path=source_path,
            request_oauth_backend=request_oauth_backend,
        )
    if settings.provider_family in RESPONSES_FAMILIES:
        payload = responses_payload(settings, assets, source_path=source_path)
        persist_request(settings, assets, source_path=source_path, endpoint="/responses", provider_payload=payload, provider_route="http")
        response = post(settings, "/responses", payload)
        return extract_responses_text(response)
    if settings.provider_family in CHAT_FAMILIES:
        payload = chat_payload(settings, assets, source_path=source_path)
        persist_request(settings, assets, source_path=source_path, endpoint="/chat/completions", provider_payload=payload, provider_route="http")
        response = post(settings, "/chat/completions", payload)
        return extract_chat_text(response)
    raise LlmOcrConfigurationError(f"optimizer_ocr Provider-Family wird nicht unterstuetzt: {settings.provider_family}")


post_json_default = post_json

# Legacy workflow monkeypatch seam kept stable while provider internals are split.
_post_json = post_json
_request_oauth_backend = request_oauth_backend_default
