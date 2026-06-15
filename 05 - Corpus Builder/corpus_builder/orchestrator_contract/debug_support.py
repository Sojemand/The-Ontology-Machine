"""Session artifact helpers for Corpus Builder debug actions."""
from __future__ import annotations

from pathlib import Path

from ..models.serialization import atomic_json_write, now_iso

_STAGE_NAME = "Corpus Builder"


def append_log(session_root: Path, line: str) -> None:
    log_path = Path(session_root) / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line.rstrip()}\n")


def cancel_requested(session_root: Path) -> bool:
    return (Path(session_root) / "cancel.request").exists()


def relative_path(session_root: Path, path: Path) -> str:
    try:
        return path.relative_to(session_root).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict) -> Path:
    atomic_json_write(Path(path), payload)
    return Path(path)


def write_snapshot(
    session_root: Path,
    *,
    status: str,
    detail: str,
    processed: int = 0,
    total: int = 0,
    counters: dict[str, int] | None = None,
) -> None:
    atomic_json_write(
        Path(session_root) / "snapshot.json",
        {
            "status": status,
            "stage": _STAGE_NAME,
            "detail": detail,
            "updated_at": now_iso(),
            "processed": int(processed),
            "total": int(total),
            "counters": dict(counters or {}),
        },
    )


def write_result(session_root: Path, payload: dict) -> dict:
    atomic_json_write(Path(session_root) / "result.json", payload)
    return payload
