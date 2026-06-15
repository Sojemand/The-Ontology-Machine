from __future__ import annotations

import os
import shutil
import time
from pathlib import Path


def latest_mtime_ns(path: Path) -> int:
    if path.is_file():
        return path.stat().st_mtime_ns
    latest = path.stat().st_mtime_ns
    for child in path.rglob("*"):
        try:
            latest = max(latest, child.stat().st_mtime_ns)
        except FileNotFoundError:
            continue
    return latest


def path_size_bytes(path: Path) -> int:
    try:
        if path.is_file():
            return path.stat().st_size
        total = 0
        for child in path.rglob("*"):
            try:
                if child.is_file():
                    total += child.stat().st_size
            except FileNotFoundError:
                continue
        return total
    except FileNotFoundError:
        return 0


def path_sort_key(path: Path) -> tuple[int, str]:
    return (latest_mtime_ns(path), path.name)


def sorted_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted([path for path in directory.iterdir() if path.is_file()], key=path_sort_key)


def sorted_dirs(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted([path for path in directory.iterdir() if path.is_dir()], key=path_sort_key)


def remove_empty_dir(directory: Path) -> None:
    if directory.exists() and not any(directory.iterdir()):
        directory.rmdir()


def file_count_exceeds(directory: Path, keep: int) -> bool:
    if not directory.exists():
        return False
    count = 0
    for path in directory.iterdir():
        if not path.is_file():
            continue
        count += 1
        if count > keep:
            return True
    return False


def delete_overflow_files(directory: Path, *, keep: int, protected_names: set[str] | None = None) -> list[Path]:
    if not directory.exists():
        return []
    protected = protected_names or set()
    paths = sorted_files(directory)
    deletable = [path for path in paths if path.name not in protected]
    overflow = len(paths) - keep
    if overflow <= 0:
        return []
    deleted_paths: list[Path] = []
    for stale_path in deletable[:overflow]:
        stale_path.unlink(missing_ok=True)
        deleted_paths.append(stale_path)
    return deleted_paths


def delete_overflow_files_older_than(
    directory: Path,
    *,
    keep: int,
    min_age_seconds: int,
    protected_names: set[str] | None = None,
) -> list[Path]:
    if not directory.exists():
        return []
    protected = protected_names or set()
    cutoff = time.time() - min_age_seconds
    paths = sorted_files(directory)
    deletable = [
        path
        for path in paths
        if path.name not in protected and _mtime_seconds(path) <= cutoff
    ]
    overflow = len(paths) - keep
    if overflow <= 0:
        return []
    deleted_paths: list[Path] = []
    for stale_path in deletable[:overflow]:
        stale_path.unlink(missing_ok=True)
        deleted_paths.append(stale_path)
    return deleted_paths


def delete_unlocked_overflow_files(directory: Path, *, keep: int, protected_names: set[str] | None = None) -> list[Path]:
    if not directory.exists():
        return []
    protected = protected_names or set()
    paths = sorted_files(directory)
    deletable = [path for path in paths if path.name not in protected]
    overflow = len(paths) - keep
    if overflow <= 0:
        return []
    deleted_paths: list[Path] = []
    for stale_path in deletable:
        if len(deleted_paths) >= overflow:
            break
        if _unlink_if_unlocked(stale_path):
            deleted_paths.append(stale_path)
    return deleted_paths


def prune_directory_children(root_dir: Path, *, keep: int, protected_names: set[str] | None = None) -> None:
    if not root_dir.exists():
        return
    protected = protected_names or set()
    children = [path for path in sorted_dirs(root_dir) if path.is_dir()]
    deletable = [path for path in children if path.name not in protected]
    overflow = len(children) - keep
    if overflow <= 0:
        return
    for stale_dir in deletable[:overflow]:
        shutil.rmtree(stale_dir, ignore_errors=True)


def prune_directory_children_by_count_and_size(
    root_dir: Path,
    *,
    keep: int,
    max_total_bytes: int,
    max_child_bytes: int | None = None,
    protected_names: set[str] | None = None,
) -> None:
    prune_directory_children(root_dir, keep=keep, protected_names=protected_names)
    if not root_dir.exists():
        return
    protected = protected_names or set()
    children = sorted_dirs(root_dir)
    if max_child_bytes is not None:
        for child in list(children):
            if child.name in protected:
                continue
            if path_size_bytes(child) > max_child_bytes:
                shutil.rmtree(child, ignore_errors=True)
    children = sorted_dirs(root_dir)
    while _children_size_bytes(children) > max_total_bytes:
        stale_dir = next((child for child in children if child.name not in protected), None)
        if stale_dir is None:
            return
        shutil.rmtree(stale_dir, ignore_errors=True)
        children = [child for child in children if child != stale_dir and child.exists()]


def prune_run_directory_root(root_dir: Path, *, dir_cap: int, file_cap: int, protected_dirs: set[str]) -> None:
    if not root_dir.exists():
        return
    for child in sorted_dirs(root_dir):
        if child.is_dir():
            delete_overflow_files(child, keep=file_cap)
            remove_empty_dir(child)
    prune_directory_children(root_dir, keep=dir_cap, protected_names=protected_dirs)


def _children_size_bytes(children: list[Path]) -> int:
    return sum(path_size_bytes(child) for child in children)


def _mtime_seconds(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def _unlink_if_unlocked(path: Path) -> bool:
    try:
        with path.open("r+b") as handle:
            if os.name == "nt":
                import msvcrt

                if path.stat().st_size == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                try:
                    import fcntl
                except ImportError:
                    return False
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        path.unlink(missing_ok=True)
        return True
    except (BlockingIOError, OSError):
        return False
