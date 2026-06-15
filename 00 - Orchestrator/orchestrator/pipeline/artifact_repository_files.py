"""Shared file operations for artifact promotion and cleanup."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from . import debug, policy, record_repository, validation


def remove_file(engine: Any, path: Path, *, allowed_roots: tuple[Path, ...] | None = None) -> None:
    if allowed_roots is not None and not validation.ensure_managed_path(engine, path, allowed_roots, action="File cleanup", noun="file path"):
        return
    try:
        path.unlink(missing_ok=True)
    except Exception:
        return
    prune_empty_dirs(path.parent, stop_at=allowed_roots or ())


def move_file_with_conflict_handling(
    engine: Any,
    source: Path,
    target: Path,
    *,
    action: str,
    content_hash: str = "",
    allowed_roots: tuple[Path, ...] | None = None,
) -> Path | None:
    if not source.exists() or not source.is_file():
        return None
    if allowed_roots is not None and not validation.ensure_managed_path(engine, source, allowed_roots, action=action, noun="source path"):
        return None
    if source == target:
        return target
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        debug.append_log(engine, f"[ERROR] {action}: target folder could not be prepared: {exc}")
        return None
    final_target = target
    if final_target.exists():
        if final_target.is_dir():
            try:
                shutil.rmtree(final_target, ignore_errors=True)
            except Exception as exc:
                debug.append_log(engine, f"[ERROR] {action}: target folder could not be cleaned: {exc}")
                return None
        if final_target.exists():
            if content_hash and path_matches_hash(final_target, content_hash):
                remove_file(engine, source, allowed_roots=allowed_roots)
                return final_target
            matching_conflict = matching_conflict_target(final_target, action=action, content_hash=content_hash)
            if matching_conflict is not None:
                remove_file(engine, source, allowed_roots=allowed_roots)
                return matching_conflict
            final_target = policy.conflict_target(final_target, action=action, content_hash=content_hash)
    try:
        shutil.move(str(source), str(final_target))
    except Exception as exc:
        debug.append_log(engine, f"[ERROR] {action}: move failed: {exc}")
        return None
    prune_empty_dirs(source.parent, stop_at=allowed_roots or ())
    return final_target


def copy_if_exists(engine: Any, source: Path, target: Path, *, allowed_roots: tuple[Path, ...] | None = None) -> None:
    if allowed_roots is not None and not validation.ensure_managed_path(engine, source, allowed_roots, action="Bundle copy", noun="artifact path"):
        return
    if source == target:
        return
    if source.exists() and source.is_file():
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            atomic_copy_file(source, target)
        except Exception as exc:
            debug.append_log(engine, f"[ERROR] Bundle copy failed: {exc}")


def atomic_copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".t", suffix=".tmp", dir=target.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as target_handle:
            fd = -1
            with source.open("rb") as source_handle:
                shutil.copyfileobj(source_handle, target_handle, length=1024 * 1024)
            target_handle.flush()
            os.fsync(target_handle.fileno())
        shutil.copystat(source, tmp_path, follow_symlinks=True)
        os.replace(tmp_path, target)
        _fsync_parent(target.parent)
    except Exception:
        if fd >= 0:
            os.close(fd)
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def path_matches_hash(path: Path, content_hash: str) -> bool:
    if not path.exists() or not content_hash:
        return False
    try:
        return record_repository.compute_hash(path) == content_hash
    except Exception:
        return False


def matching_conflict_target(target: Path, *, action: str, content_hash: str) -> Path | None:
    if not content_hash:
        return None
    for candidate in policy.conflict_target_candidates(target, action=action, content_hash=content_hash):
        if not candidate.exists():
            return None
        if candidate.is_file() and path_matches_hash(candidate, content_hash):
            return candidate
    return None


def prune_empty_dirs(path: Path, *, stop_at: tuple[Path, ...] | None = None) -> None:
    stop_paths = {validation.resolved_path(root) for root in (stop_at or ())}
    current = path
    while current.exists():
        if validation.resolved_path(current) in stop_paths:
            break
        try:
            current.rmdir()
        except OSError:
            break
        if current == current.parent:
            break
        current = current.parent


def _fsync_parent(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)
