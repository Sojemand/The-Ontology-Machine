"""Shared state helpers for the debug-host UI."""

from __future__ import annotations

DEFAULT_STATE = {
    "input_path": "",
    "source_path": "",
    "format": "",
    "doc_type": "",
    "max_size_mb": "",
    "batch_size": "0",
    "worker_count": "1",
    "use_processed_hashes": True,
    "raw_path": "",
    "raw_root": "",
    "artifact_import_path": "",
    "dismissed_artifact_paths": [],
    "persist_page_images_in_db": False,
    "check_free_text": True,
    "check_context_scalars": True,
    "check_content_fields": True,
    "check_rows": True,
}


def set_text(widget, value: str) -> None:
    if widget is None:
        return
    if hasattr(widget, "set"):
        widget.set(value)
        return
    widget.delete(0, "end")
    if value:
        widget.insert(0, value)


def set_bool(variable, value: bool) -> None:
    if variable is not None and hasattr(variable, "set"):
        variable.set(bool(value))


def widget_text(widget) -> str:
    if widget is None or not hasattr(widget, "get"):
        return ""
    return text_value(widget.get())


def bool_value(variable, *, default: bool) -> bool:
    if variable is None or not hasattr(variable, "get"):
        return default
    return bool(variable.get())


def text_value(value: object) -> str:
    return str(value or "").strip()


def int_value(value: object, *, default: int = 0) -> int:
    try:
        return int(str(value or default).strip() or default)
    except (TypeError, ValueError):
        return default
