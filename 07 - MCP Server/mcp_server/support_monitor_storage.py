from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .support_monitor_redaction import redact
from .support_monitor_types import ASSESSMENTS_NAME, DISMISSED_NAME, EVENTS_NAME, OUTBOX_DIR_NAME, REPORTS_DIR_NAME, SUPPORT_DIR_NAME, SupportError

WINDOWS_PATH_BUDGET_CHARS = 300
JSONL_RECORD_HARD_CAP = 5000
JSONL_BYTES_HARD_CAP = 16 * 1024 * 1024


def state_root() -> Path:
    return Path(__file__).resolve().parents[1] / "state" / SUPPORT_DIR_NAME


def load_events() -> list[dict[str, Any]]:
    return load_jsonl(events_path())


def load_assessments() -> list[dict[str, Any]]:
    return load_jsonl(assessments_path())


def load_dismissed() -> set[str]:
    return {str(item.get("incident_id") or "") for item in load_jsonl(dismissed_path()) if str(item.get("incident_id") or "").strip()}


def events_path() -> Path:
    return state_root() / EVENTS_NAME


def assessments_path() -> Path:
    return state_root() / ASSESSMENTS_NAME


def dismissed_path() -> Path:
    return state_root() / DISMISSED_NAME


def reports_dir() -> Path:
    path = state_root() / REPORTS_DIR_NAME
    ensure_path_budget(path, "support reports directory")
    path.mkdir(parents=True, exist_ok=True)
    return path


def outbox_dir() -> Path:
    path = state_root() / OUTBOX_DIR_NAME
    ensure_path_budget(path, "support outbox directory")
    path.mkdir(parents=True, exist_ok=True)
    return path


def append_jsonl(
    path: Path,
    payload: dict[str, Any],
    *,
    max_records: int | None = None,
    max_bytes: int | None = None,
) -> None:
    ensure_path_budget(path, "support state file")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    prune_jsonl(path, max_records=max_records, max_bytes=max_bytes)


def prune_jsonl(path: Path, *, max_records: int | None = None, max_bytes: int | None = None) -> None:
    max_records = JSONL_RECORD_HARD_CAP if max_records is None else max(1, int(max_records))
    max_bytes = JSONL_BYTES_HARD_CAP if max_bytes is None else max(0, int(max_bytes))
    try:
        data = path.read_bytes()
    except OSError:
        return
    lines = [line for line in data.splitlines() if line.strip()]
    if len(lines) <= max_records and (max_bytes <= 0 or len(data) <= max_bytes):
        return

    kept = lines[-max_records:]
    if max_bytes > 0:
        total = _jsonl_size(kept)
        while len(kept) > 1 and total > max_bytes:
            dropped = kept.pop(0)
            total -= len(dropped) + 1

    new_data = b"\n".join(kept)
    if new_data:
        new_data += b"\n"
    tmp_path = path.with_name(".__jsonl.tmp")
    try:
        tmp_path.write_bytes(new_data)
        tmp_path.replace(path)
    except OSError:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _jsonl_size(lines: list[bytes]) -> int:
    if not lines:
        return 0
    return sum(len(line) for line in lines) + len(lines)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            items.append(payload)
    return items


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"path": str(path), "load_error": "unavailable"}
    return redact(payload) if isinstance(payload, dict) else {"path": str(path), "load_error": "not_object"}


def required_text(value: object, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SupportError(f"{label} is required.")
    return text


def ensure_path_budget(path: Path, label: str) -> None:
    path_text = str(path)
    if len(path_text) <= WINDOWS_PATH_BUDGET_CHARS:
        return
    raise SupportError(
        f"{label} would be {len(path_text)} characters and exceeds the "
        f"Windows path budget of {WINDOWS_PATH_BUDGET_CHARS}. "
        "Choose a shorter support state, workspace, or output path."
    )


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [name for name in globals() if not name.startswith("_")]
