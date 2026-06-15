"""Repository stage for persisted debug-host session storage."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ..bootstrap import STATE_ROOT
from .types import DebugCleanupSummary

DEBUG_SESSION_DIR_HARD_CAP = 20
DEBUG_SESSION_TOTAL_BYTES_HARD_CAP = 256 * 1024 * 1024


@dataclass(frozen=True)
class _SessionDir:
    path: Path
    size_bytes: int
    mtime: float


def clear_sessions(*, state_root: Path | None = None) -> DebugCleanupSummary:
    root = session_root(state_root=state_root)
    removed_sessions = 0
    for path in _session_dirs(root):
        shutil.rmtree(path)
        removed_sessions += 1
    if root.exists() and root.is_dir() and not any(root.iterdir()):
        root.rmdir()
    return DebugCleanupSummary(removed_sessions=removed_sessions)


def has_sessions(*, state_root: Path | None = None) -> bool:
    root = session_root(state_root=state_root)
    return any(True for _ in _session_dirs(root))


def prune_sessions(
    *,
    state_root: Path | None = None,
    keep_dirs: int = DEBUG_SESSION_DIR_HARD_CAP,
    max_total_bytes: int = DEBUG_SESSION_TOTAL_BYTES_HARD_CAP,
    protected_session_id: str = "",
) -> list[Path]:
    keep_dirs = max(1, int(keep_dirs))
    max_total_bytes = max(0, int(max_total_bytes))
    protected = str(protected_session_id or "").strip()
    entries = _session_entries(session_root(state_root=state_root))
    remaining = sorted(entries, key=lambda item: (item.mtime, item.path.name))
    total_bytes = sum(item.size_bytes for item in remaining)
    removed: list[Path] = []

    while len(remaining) > keep_dirs:
        candidate = _oldest_removable(remaining, protected)
        if candidate is None:
            break
        if _remove_session_dir(candidate.path):
            removed.append(candidate.path)
            total_bytes -= candidate.size_bytes
        remaining.remove(candidate)

    while max_total_bytes > 0 and total_bytes > max_total_bytes:
        candidate = _oldest_removable(remaining, protected)
        if candidate is None:
            break
        if _remove_session_dir(candidate.path):
            removed.append(candidate.path)
            total_bytes -= candidate.size_bytes
        remaining.remove(candidate)

    return removed


def session_root(*, state_root: Path | None = None) -> Path:
    return Path(state_root or STATE_ROOT) / "debug_sessions"


def _session_dirs(root: Path) -> tuple[Path, ...]:
    if not root.exists() or not root.is_dir():
        return ()
    return tuple(
        path
        for path in root.iterdir()
        if path.is_dir() and path.name.startswith("dbg_")
    )


def _session_entries(root: Path) -> list[_SessionDir]:
    entries: list[_SessionDir] = []
    for path in _session_dirs(root):
        try:
            stat = path.stat()
        except OSError:
            continue
        entries.append(_SessionDir(path=path, size_bytes=_directory_size(path), mtime=stat.st_mtime))
    return entries


def _oldest_removable(entries: list[_SessionDir], protected_session_id: str) -> _SessionDir | None:
    return next((item for item in entries if item.path.name != protected_session_id), None)


def _directory_size(path: Path) -> int:
    total = 0
    try:
        for item in path.rglob("*"):
            try:
                if item.is_file():
                    total += item.stat().st_size
            except OSError:
                continue
    except OSError:
        return total
    return total


def _remove_session_dir(path: Path) -> bool:
    try:
        shutil.rmtree(path)
    except OSError:
        return False
    return not path.exists()
