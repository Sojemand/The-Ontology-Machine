"""Snapshot and log rendering for the Orchestrator desktop UI."""

from __future__ import annotations

from pathlib import Path

from ..models import PipelineSnapshot
from . import repository, view_model


def apply_snapshot(app, snapshot: PipelineSnapshot) -> None:
    app._progress.set(view_model.progress_value(snapshot))
    app._status_label.configure(text=view_model.status_line(snapshot), text_color=view_model.status_line_color(snapshot))
    for name, value in view_model.counter_values(snapshot).items():
        app._counter_labels[name].configure(text=value)
    apply_database_status(app)
    if hasattr(app, "_route_labels"):
        for name, value in view_model.route_values(snapshot).items():
            app._route_labels[name].configure(text=view_model.compact_stage_detail(value, limit=96))
    for name, (status, detail) in view_model.stage_values(snapshot).items():
        stage = snapshot.stage_statuses[name]
        status_label, detail_label, progress_label = app._stage_labels[name]
        status_label.configure(text=status, text_color=view_model.stage_text_color(status))
        detail_label.configure(text=view_model.compact_stage_detail(detail))
        progress_label.configure(text=view_model.stage_progress_text(stage))


def apply_database_status(app) -> None:
    labels = getattr(app, "_database_labels", None)
    if not isinstance(labels, dict):
        return
    fields = repository.read_fields(app)
    status = getattr(app, "_database_status", {}) if isinstance(getattr(app, "_database_status", None), dict) else {}
    selected_db = str(status.get("selected_database") or fields.selected_corpus_db_path or "-")
    for name, value in {
        "Selected Database": selected_db,
        "DB State": str(status.get("db_state") or "Not loaded yet"),
        "Active DB Release": str(status.get("active_release") or "-"),
        "Run Release": _run_release_label(fields),
    }.items():
        if name in labels:
            labels[name].configure(text=view_model.compact_stage_detail(value, limit=112))


def append_log(app, line: str) -> None:
    formatted_line = view_model.format_log_line(line)
    _log_lines(app).append(formatted_line)
    if not hasattr(app, "_log_box"):
        return
    app._log_box.configure(state="normal")
    app._log_box.insert("end", formatted_line)
    if hasattr(app._log_box, "see"):
        app._log_box.see("end")
    app._log_box.configure(state="disabled")


def clear_log(app) -> None:
    _log_lines(app).clear()
    if not hasattr(app, "_log_box"):
        return
    app._log_box.configure(state="normal")
    app._log_box.delete("1.0", "end")
    app._log_box.configure(state="disabled")


def sync_log_box(app) -> None:
    if not hasattr(app, "_log_box"):
        return
    app._log_box.configure(state="normal")
    app._log_box.delete("1.0", "end")
    app._log_box.insert("end", "".join(_log_lines(app)))
    if hasattr(app._log_box, "see"):
        app._log_box.see("end")
    app._log_box.configure(state="disabled")


def _log_lines(app) -> list[str]:
    lines = getattr(app, "_log_lines", None)
    if lines is None:
        lines = []
        app._log_lines = lines
    return lines


def _run_release_label(fields) -> str:
    if fields.semantic_release_mode == "override_selected":
        release_path = str(fields.semantic_release_path or "").strip()
        if release_path:
            return f"Override | {Path(release_path).name}"
        return "Override | release missing"
    return "Use database release"
