"""Small JSON HTTP helpers for Orchestrator OAuth exchanges."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class JsonHttpResponse:
    status_code: int
    headers: dict[str, str]
    body: dict[str, Any]
    raw_text: str


def post_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 60,
) -> JsonHttpResponse:
    body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=body_bytes,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            **(headers or {}),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw_text = response.read().decode("utf-8", errors="replace")
            return JsonHttpResponse(
                status_code=int(getattr(response, "status", 200)),
                headers=dict(response.headers.items()),
                body=_decode_json(raw_text),
                raw_text=raw_text,
            )
    except HTTPError as exc:
        raw_text = exc.read().decode("utf-8", errors="replace")
        return JsonHttpResponse(
            status_code=int(exc.code),
            headers=dict(exc.headers.items()),
            body=_decode_json(raw_text),
            raw_text=raw_text,
        )
    except URLError as exc:
        raise RuntimeError(f"OAuth HTTP request failed: {exc}") from exc


def _decode_json(raw_text: str) -> dict[str, Any]:
    if not raw_text.strip():
        return {}
    try:
        data = json.loads(raw_text)
    except ValueError:
        return {"raw_text": raw_text}
    return data if isinstance(data, dict) else {"raw_text": raw_text}
