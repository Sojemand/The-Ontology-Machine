"""Shared view helpers for the debug-host UI."""

from __future__ import annotations


def session_status(session) -> str:
    if session.result is not None:
        return session.result.status.upper()
    if session.snapshot is not None:
        return session.snapshot.status.upper()
    return "RUNNING"


def session_detail(session) -> str:
    if session.result is not None:
        return session.result.summary
    if session.snapshot is not None:
        return session.snapshot.detail
    return ""


def metrics_text(session) -> str:
    counters: dict[str, object] = {}
    if session.snapshot is not None:
        counters.update(session.snapshot.counters)
    if session.result is not None:
        counters.update(session.result.metrics)
    if not counters:
        return ""
    return " | ".join(f"{key}={value}" for key, value in sorted(counters.items()))


def declared_output_lines(session) -> list[str]:
    if session is None or session.result is None or not session.result.outputs:
        return []
    return [
        str(value)
        for _group, values in sorted(session.result.outputs.items())
        for value in values
    ]


def merge_lines(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for line in group:
            text = str(line).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            merged.append(text)
    return merged


def set_row_visible(row, visible: bool) -> None:
    if row is None:
        return
    setattr(row, "visible", visible)
    if not hasattr(row, "pack") or not hasattr(row, "pack_forget"):
        return
    if visible:
        row.pack(fill="x")
        return
    row.pack_forget()


def set_box(box, text: str) -> None:
    if box is None:
        return
    box.configure(state="normal")
    box.delete("1.0", "end")
    if text:
        box.insert("1.0", text)
    box.configure(state="disabled")


def set_label(label, text: str) -> None:
    if label is not None:
        label.configure(text=text)
