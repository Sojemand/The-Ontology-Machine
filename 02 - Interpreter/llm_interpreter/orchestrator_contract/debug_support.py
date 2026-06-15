"""Session artifact helpers for interpreter debug runs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..models import atomic_json_write


def append_log(session_root: Path, line: str) -> None:
    log_path = session_root / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line.rstrip()}\n")


def cancel_requested(session_root: Path) -> bool:
    return (session_root / "cancel.request").exists()


def relative_path(session_root: Path, path: Path) -> str:
    try:
        return path.relative_to(session_root).as_posix()
    except ValueError:
        return str(path)


def write_snapshot(
    session_root: Path,
    *,
    status: str,
    detail: str,
    processed: int | None = None,
    total: int | None = None,
    counters: dict[str, int] | None = None,
) -> None:
    snapshot_total = 1 if total is None else max(0, int(total))
    snapshot_processed = 1 if processed is None and status in {"ok", "cancelled"} else max(0, int(processed or 0))
    atomic_json_write(
        session_root / "snapshot.json",
        {
            "status": status,
            "stage": "Interpreter",
            "detail": detail,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "processed": min(snapshot_processed, snapshot_total),
            "total": snapshot_total,
            "counters": dict(counters or {}),
        },
    )


def write_result(session_root: Path, payload: dict) -> dict:
    atomic_json_write(session_root / "result.json", payload)
    return payload
