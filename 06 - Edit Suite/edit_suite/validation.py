"""Hard validation for suite-local state writes."""

from __future__ import annotations

import hashlib
from pathlib import Path

MAX_SAFE_FILENAME_LENGTH = 40
_HASH_LENGTH = 10


def ensure_state_child(state_root: Path, target: Path) -> Path:
    resolved_root = state_root.resolve()
    resolved_target = target.resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"State write path is outside {resolved_root}: {resolved_target}") from exc
    return resolved_target


def safe_filename(value: str, *, fallback: str, max_length: int = MAX_SAFE_FILENAME_LENGTH) -> str:
    cleaned = str(value or "").replace("/", "_").replace("\\", "_").strip()
    for char in ':*?"<>|':
        cleaned = cleaned.replace(char, "_")
    while ".." in cleaned:
        cleaned = cleaned.replace("..", ".")
    cleaned = cleaned.strip(" ._")
    return _shorten_name(cleaned or fallback, fallback=fallback, max_length=max_length)


def _shorten_name(name: str, *, fallback: str, max_length: int) -> str:
    limit = max(16, int(max_length))
    if len(name) <= limit:
        return name
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:_HASH_LENGTH]
    suffix = Path(name).suffix
    if len(suffix) > 12 or len(suffix) >= limit - _HASH_LENGTH - 2:
        suffix = ""
    stem = name[: -len(suffix)] if suffix else name
    head_budget = max(1, limit - len(digest) - len(suffix) - 1)
    head = stem[:head_budget].rstrip(" ._-")
    if not head:
        head = str(fallback or "file")[:head_budget].rstrip(" ._-") or "file"
    return f"{head}-{digest}{suffix}"


def require_json_object(payload: object, *, label: str) -> dict:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return payload
