"""HTTP transport helpers for the OpenAI Responses API provider."""
from __future__ import annotations

import json
import socket
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from .base import ProviderError


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


def request_openai(
    *,
    base_url: str,
    api_key: str | None,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int,
    extra_headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], str]:
    body = None
    headers: dict[str, str] = {}
    key = str(api_key or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if extra_headers:
        headers.update(extra_headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    query_string = f"?{urllib.parse.urlencode(query)}" if query else ""
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}{query_string}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return (
                int(response.getcode()),
                {str(key).lower(): str(value) for key, value in response.headers.items()},
                response.read().decode("utf-8", errors="replace"),
            )
    except urllib.error.HTTPError as exc:
        return (
            exc.code,
            {str(key).lower(): str(value) for key, value in exc.headers.items()},
            exc.read().decode("utf-8", errors="replace"),
        )
    except socket.timeout as exc:
        raise ProviderError(f"Provider Timeout nach {timeout}s") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"Provider nicht erreichbar: {exc.reason}") from exc
    except OSError as exc:
        raise ProviderError(f"Provider Anfrage fehlgeschlagen: {exc}") from exc
