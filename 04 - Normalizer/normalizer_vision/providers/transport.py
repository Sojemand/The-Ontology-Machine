"""HTTP transport helpers for the Normalizer OpenAI provider."""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests


def build_headers(api_key: str | None, *, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    key = str(api_key or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if extra_headers:
        headers.update(extra_headers)
    return headers


def responses_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/responses"


def request_id(response: Any) -> str:
    return response.headers.get("x-request-id") or response.headers.get("request-id") or "-"


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        seconds = (retry_at - datetime.now(timezone.utc)).total_seconds()
    return seconds if seconds > 0 else None


def post_responses(transport: Any, *, endpoint: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> Any:
    return transport.post(endpoint, json=payload, headers=headers, timeout=(10, timeout))


def post_json(transport: Any, *, endpoint: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> Any:
    return transport.post(endpoint, json=payload, headers=headers, timeout=(10, timeout))


def get_models(transport: Any, *, base_url: str, headers: dict[str, str], timeout: int) -> Any:
    return transport.get(f"{base_url.rstrip('/')}/models", headers=headers, timeout=timeout)
