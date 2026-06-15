"""Retention limits for resettable pipeline runtime history."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

RUN_HISTORY_DIR_HARD_CAP = 20
RUN_HISTORY_TOTAL_BYTES_HARD_CAP = 256 * 1024 * 1024


@dataclass(frozen=True)
class _RunDir:
    path: Path
    size_bytes: int
    mtime: float


def prune_run_history(
    runtime_root: Path,
    *,
    keep_dirs: int = RUN_HISTORY_DIR_HARD_CAP,
    max_total_bytes: int = RUN_HISTORY_TOTAL_BYTES_HARD_CAP,
    protected_names: set[str] | None = None,
) -> list[Path]:
    """Delete oldest completed run directories until history is bounded."""

    keep_dirs = max(1, int(keep_dirs))
    max_total_bytes = max(0, int(max_total_bytes))
    protected = {name for name in (protected_names or set()) if name}
    entries = _run_dirs(runtime_root)
    if not entries:
        return []

    remaining = sorted(entries, key=lambda item: (item.mtime, item.path.name))
    total_bytes = sum(item.size_bytes for item in remaining)
    removed: list[Path] = []

    while len(remaining) > keep_dirs:
        candidate = _oldest_removable(remaining, protected)
        if candidate is None:
            break
        if _remove_run_dir(candidate.path):
            removed.append(candidate.path)
            total_bytes -= candidate.size_bytes
        remaining.remove(candidate)

    while max_total_bytes > 0 and total_bytes > max_total_bytes:
        candidate = _oldest_removable(remaining, protected)
        if candidate is None:
            break
        if _remove_run_dir(candidate.path):
            removed.append(candidate.path)
            total_bytes -= candidate.size_bytes
        remaining.remove(candidate)

    return removed


def _run_dirs(runtime_root: Path) -> list[_RunDir]:
    try:
        children = list(runtime_root.iterdir())
    except OSError:
        return []
    entries: list[_RunDir] = []
    for path in children:
        try:
            if not path.is_dir() or path.is_symlink():
                continue
            stat = path.stat()
        except OSError:
            continue
        entries.append(_RunDir(path=path, size_bytes=_directory_size(path), mtime=stat.st_mtime))
    return entries


def _oldest_removable(entries: list[_RunDir], protected_names: set[str]) -> _RunDir | None:
    return next((item for item in entries if item.path.name not in protected_names), None)


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


def _remove_run_dir(path: Path) -> bool:
    try:
        shutil.rmtree(path)
    except OSError:
        return False
    return not path.exists()
