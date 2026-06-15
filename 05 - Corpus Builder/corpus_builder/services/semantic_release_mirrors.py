"""Filesystem mirror helpers for semantic release activation."""

from __future__ import annotations

from pathlib import Path

from ..models.serialization import atomic_bytes_write


def read_existing_bytes(path: Path) -> bytes | None:
    if not path.exists():
        return None
    return path.read_bytes()


def restore_release_file(path: Path, previous_bytes: bytes | None, *, cause: Exception | None = None) -> None:
    try:
        if previous_bytes is None:
            path.unlink(missing_ok=True)
            return
        atomic_bytes_write(path, previous_bytes)
    except Exception as restore_exc:
        if cause is None:
            raise
        raise RuntimeError(
            f"Semantic Release Mirror konnte nach Commit-Fehler nicht wiederhergestellt werden: {restore_exc}"
        ) from cause
