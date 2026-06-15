from __future__ import annotations

from pathlib import Path
from typing import Any


def selected_release_path(ui_state: Any) -> Path | None:
    if str(getattr(ui_state, "semantic_release_mode", "database_default") or "").strip().lower() != "override_selected":
        return None
    text = str(getattr(ui_state, "semantic_release_path", "") or "").strip()
    return Path(text) if text else None


def dict_payload(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def text_value(value: Any) -> str:
    return str(value or "").strip()


def int_value(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except Exception:
        return 0


def short_id(value: str) -> str:
    text = text_value(value)
    return text[:16] if text else ""
