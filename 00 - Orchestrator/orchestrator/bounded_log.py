"""Bounded append helpers for resettable local log files."""

from __future__ import annotations

from pathlib import Path

TRUNCATION_MARKER = "[... log truncated to stay within retention limit ...]\n"


def append_text(path: Path, text: str, *, max_bytes: int) -> None:
    max_bytes = max(1, int(max_bytes))
    path.parent.mkdir(parents=True, exist_ok=True)
    if _rewrite_oversized_text(path, text, max_bytes=max_bytes):
        return
    _trim_for_append(path, incoming_bytes=len(text.encode("utf-8")), max_bytes=max_bytes)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _rewrite_oversized_text(path: Path, text: str, *, max_bytes: int) -> bool:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return False
    path.write_text(_truncated_text(encoded, max_bytes=max_bytes), encoding="utf-8", newline="\n")
    return True


def _trim_for_append(path: Path, *, incoming_bytes: int, max_bytes: int) -> None:
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return
    except OSError:
        return
    if size + incoming_bytes <= max_bytes:
        return

    marker_bytes = TRUNCATION_MARKER.encode("utf-8")
    trim_budget = max_bytes - incoming_bytes
    if trim_budget < len(marker_bytes):
        try:
            path.write_text("", encoding="utf-8", newline="\n")
        except OSError:
            pass
        return
    keep_bytes = max(0, trim_budget - len(marker_bytes))
    try:
        with path.open("rb") as handle:
            if keep_bytes:
                handle.seek(-keep_bytes, 2)
                tail_bytes = handle.read()
            else:
                tail_bytes = b""
    except OSError:
        return
    path.write_text(_truncated_text(tail_bytes, max_bytes=trim_budget), encoding="utf-8", newline="\n")


def _truncated_text(tail_bytes: bytes, *, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    marker_bytes = TRUNCATION_MARKER.encode("utf-8")
    if max_bytes <= len(marker_bytes):
        return marker_bytes[:max_bytes].decode("utf-8", errors="ignore")
    tail_budget = max_bytes - len(marker_bytes)
    tail = tail_bytes[-tail_budget:].decode("utf-8", errors="ignore")
    return TRUNCATION_MARKER + tail
