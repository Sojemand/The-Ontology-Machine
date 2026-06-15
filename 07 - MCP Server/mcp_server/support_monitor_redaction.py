from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

SECRET_KEY_RE = re.compile(r"(api[_-]?key|authorization|credential|password|secret|token)", re.IGNORECASE)
API_KEY_RE = re.compile(r"\b(sk-[A-Za-z0-9_-]{12,}|[A-Za-z0-9_-]{32,})\b")


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def message_fingerprint(message: str) -> str:
    return re.sub(r"\d+", "<n>", message.strip().casefold())[:160]


def highest_severity(items: list[str]) -> str:
    order = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    return max(items or ["error"], key=lambda item: order.get(item, 2))


def stacktrace_excerpt(stacktrace: str) -> str:
    if not stacktrace:
        return ""
    lines = [line for line in stacktrace.splitlines() if line.strip()]
    return "\n".join(lines[-8:])


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            text_key = str(key)
            result[text_key] = "[REDACTED]" if SECRET_KEY_RE.search(text_key) else redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(value: str) -> str:
    text = API_KEY_RE.sub("[REDACTED_TOKEN]", value)
    home = str(Path.home())
    if home and home in text:
        text = text.replace(home, "%USERPROFILE%")
    pipeline_root = str(Path(__file__).resolve().parents[2])
    if pipeline_root in text:
        text = text.replace(pipeline_root, "%PIPELINE_ROOT%")
    return text


__all__ = [name for name in globals() if not name.startswith("_")]
