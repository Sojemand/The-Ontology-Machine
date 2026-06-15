from __future__ import annotations

import json
import re
import socket
from typing import Any
import urllib.error
import urllib.request

from .errors import LlmOcrResponseError
from .settings import LlmOcrSettings

_REDACTION_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (re.compile(r'(?i)(["\']?(?:access_token|refresh_token|id_token|api_key|authorization)["\']?\s*[:=]\s*["\']?)([^"\'\s,}]+)'), r"\1[REDACTED]"),
    (re.compile(r"(?i)\b(?:OPENAI_API_KEY|OPTIMIZER_OCR_API_KEY|OPTIMIZER_OCR_OAUTH_ACCESS_TOKEN)\s*[:=]\s*([^\s,;]+)"), "OPTIMIZER_OCR_SECRET=[REDACTED]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]+\b"), "sk-[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+\.[A-Za-z0-9._-]+\b"), "[REDACTED_JWT]"),
)


def post_json(settings: LlmOcrSettings, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if settings.bearer_token:
        headers["Authorization"] = f"Bearer {settings.bearer_token}"
    request = urllib.request.Request(
        f"{settings.base_url.rstrip('/')}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.timeout_seconds) as response:
            response_text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LlmOcrResponseError(f"LLM-OCR Provider API Fehler {exc.code}: {sanitize_provider_error(detail)}") from exc
    except socket.timeout as exc:
        raise LlmOcrResponseError(f"LLM-OCR Provider Timeout nach {settings.timeout_seconds}s") from exc
    except urllib.error.URLError as exc:
        raise LlmOcrResponseError(f"LLM-OCR Provider nicht erreichbar: {exc.reason}") from exc
    except OSError as exc:
        raise LlmOcrResponseError(f"LLM-OCR Provider Anfrage fehlgeschlagen: {exc}") from exc
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise LlmOcrResponseError("LLM-OCR Provider lieferte ungueltiges JSON.") from exc
    if not isinstance(parsed, dict):
        raise LlmOcrResponseError("LLM-OCR Provider lieferte kein JSON-Objekt.")
    return parsed


def sanitize_provider_error(value: str) -> str:
    sanitized = str(value or "")
    for pattern, replacement in _REDACTION_RULES:
        sanitized = pattern.sub(replacement, sanitized)
    text = " ".join(sanitized.split())
    return text[:500] or "unbekannter Fehler"
