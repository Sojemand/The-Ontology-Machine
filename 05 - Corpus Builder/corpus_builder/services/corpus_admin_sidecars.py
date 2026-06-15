"""Corpus DB WAL sidecar cleanup helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def cleanup_idle_wal_sidecars(db_path: Path) -> dict[str, Any]:
    wal_path = db_path.with_name(db_path.name + "-wal")
    shm_path = db_path.with_name(db_path.name + "-shm")
    result: dict[str, Any] = {"attempted": True, "removed": [], "skipped": []}
    wal_is_empty_or_missing = True
    if wal_path.exists():
        wal_size = wal_path.stat().st_size
        if wal_size == 0:
            wal_is_empty_or_missing = remove_sidecar(wal_path, result)
        else:
            wal_is_empty_or_missing = False
            result["skipped"].append({"path": str(wal_path), "reason": "wal_not_empty", "size_bytes": wal_size})
    if shm_path.exists():
        if wal_is_empty_or_missing:
            remove_sidecar(shm_path, result)
        else:
            result["skipped"].append({"path": str(shm_path), "reason": "wal_not_empty_or_locked"})
    result["remaining"] = [str(path) for path in (wal_path, shm_path) if path.exists()]
    return result


def remove_sidecar(path: Path, result: dict[str, Any]) -> bool:
    try:
        path.unlink()
    except OSError as exc:
        result["skipped"].append({"path": str(path), "reason": type(exc).__name__, "detail": str(exc)})
        return False
    result["removed"].append(str(path))
    return True
