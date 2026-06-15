"""Pure helpers for GUI state rendering and tests."""
from __future__ import annotations

import re

from ..models import PipelineSnapshot, StageSnapshot
from . import theme

_SUCCESS_STATUSES = {
    theme.STATUS_DONE.casefold(),
    "ok",
    "loaded",
    "archived_and_loaded",
    "skipped",
}
_WARNING_STATUSES = {
    "aborted",
    "initializing...",
    "review",
    "processing...",
    "warn",
}
_ERROR_STATUSES = {
    theme.STATUS_ERROR.casefold(),
    "error",
    "fail",
}
def progress_value(snapshot: PipelineSnapshot) -> float:
    if snapshot.total <= 0:
        return 0.0
    return min(1.0, max(0.0, snapshot.completed / snapshot.total))


def counter_values(snapshot: PipelineSnapshot) -> dict[str, str]:
    return {
        "Pending": str(snapshot.pending),
        "Success": str(snapshot.success),
        "Errors": str(snapshot.errors),
        "Needs Review": str(snapshot.needs_review),
        "Retries": str(snapshot.retries),
    }


def stage_values(snapshot: PipelineSnapshot) -> dict[str, tuple[str, str]]:
    return {
        name: (stage.status, stage.detail)
        for name, stage in snapshot.stage_statuses.items()
    }


def stage_progress_text(stage: StageSnapshot) -> str:
    if stage.progress_total <= 0:
        return ""
    label = stage.progress_label or "Items"
    return f"{stage.progress_current}/{stage.progress_total} {label}"


def route_values(snapshot: PipelineSnapshot) -> dict[str, str]:
    return {
        "Route Family": snapshot.current_route_family or "-",
        "Optimizer": snapshot.current_optimizer_module or "-",
        "Interpreter": snapshot.current_interpreter_module or "-",
        "Intake Reason": snapshot.current_intake_reason or "-",
    }


def compact_stage_detail(detail: str, *, limit: int = 72) -> str:
    normalized = re.sub(r"\s+", " ", detail or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def status_line(snapshot: PipelineSnapshot) -> str:
    if snapshot.aborted:
        return (
            f"Aborted | "
            f"File: {snapshot.current_file or '-'} | "
            f"Attempt: {snapshot.current_attempt or 0}"
        )
    if snapshot.is_running and not snapshot.total:
        return "Initializing..."
    if not snapshot.total:
        stage_summary = _latest_stage_summary(snapshot)
        if stage_summary:
            return stage_summary
        return theme.STATUS_READY
    return (
        f"{snapshot.completed}/{snapshot.total} completed | "
        f"File: {snapshot.current_file or '-'} | "
        f"Attempt: {snapshot.current_attempt or 0}"
    )


def format_log_line(line: str) -> str:
    return line.rstrip() + "\n"


def stage_text_color(status: str) -> str | tuple[str, str]:
    normalized = status.strip().casefold()
    if normalized in _SUCCESS_STATUSES:
        return theme.COLOR_SUCCESS
    if normalized in _WARNING_STATUSES:
        return theme.COLOR_WARNING
    if normalized in _ERROR_STATUSES:
        return theme.COLOR_ERROR
    return theme.COLOR_TEXT


def status_line_color(snapshot: PipelineSnapshot) -> str | tuple[str, str]:
    if snapshot.aborted:
        return theme.COLOR_WARNING
    if snapshot.errors:
        return theme.COLOR_ERROR
    if snapshot.needs_review:
        return theme.COLOR_WARNING
    if snapshot.is_running:
        return theme.COLOR_WARNING
    if snapshot.total and snapshot.completed == snapshot.total:
        return theme.COLOR_SUCCESS
    return theme.COLOR_TEXT


def _latest_stage_summary(snapshot: PipelineSnapshot) -> str:
    for stage in reversed(list(snapshot.stage_statuses.values())):
        if stage.status == theme.STATUS_READY and not stage.detail:
            continue
        if stage.detail:
            return f"{stage.status} | {compact_stage_detail(stage.detail, limit=96)}"
        if stage.status != theme.STATUS_READY:
            return stage.status
    return ""
