"""Formatting and policy helpers for operation progress dialogs."""

from __future__ import annotations

from typing import Any

from . import theme

LONG_RUNNING_ACTIONS = {
    "rebuild_from_artifacts",
    "create_and_rebuild_new_corpus_db",
    "generate_embeddings",
}
WARNING_COLOR = "#E6B800"


def should_show(action_link: dict) -> bool:
    if action_link.get("show_progress_dialog") is False:
        return False
    if isinstance(action_link.get("progress_dialog"), dict):
        return True
    if action_link.get("show_progress_dialog") is True:
        return True
    return str(action_link.get("action") or "").strip() in LONG_RUNNING_ACTIONS


def completion_detail(response: dict[str, Any], *, status: str) -> str:
    lines = [f"Status: {status}"]
    count = response.get("count")
    if count is not None:
        lines.append(f"Count: {count}")
    message = str(response.get("headline") or response.get("reason") or response.get("message") or "").strip()
    if message:
        lines.append(message)
    summary_lines = response.get("summary_lines")
    if isinstance(summary_lines, list):
        lines.extend(str(item) for item in summary_lines if str(item).strip())
    return "\n".join(lines)


def status_color(status: str) -> str:
    normalized = status.casefold()
    if normalized in {"error", "failed", "cancelled"}:
        return theme.COLOR_ERROR
    if normalized in {"disabled", "warning", "warnung"}:
        return WARNING_COLOR
    return theme.COLOR_SUCCESS


def format_duration(seconds: int) -> str:
    minutes, rest = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{rest:02d}"
    return f"{minutes:02d}:{rest:02d}"
