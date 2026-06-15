"""Snapshot file helpers for orchestrator contract actions."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

SNAPSHOT_REPLACE_ATTEMPTS = 8
SNAPSHOT_REPLACE_RETRY_SECONDS = 0.08
SNAPSHOT_TRANSIENT_WINERRORS = {5, 32}


def _snapshot_file_writer(snapshot_path: str, *, artifact_root: str = ""):
    if not snapshot_path:
        return None
    target = _snapshot_target(snapshot_path, artifact_root=artifact_root)
    error_cases_root = _error_cases_root(artifact_root)

    def write_snapshot(snapshot) -> None:
        payload = snapshot.to_dict() if hasattr(snapshot, "to_dict") else snapshot
        if not isinstance(payload, dict):
            payload = {"snapshot": str(payload)}
        if error_cases_root is not None:
            payload["error_cases_folder"] = _error_cases_folder_snapshot(error_cases_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target.with_name(f"{target.name}.{uuid4().hex}.tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, indent=2))
                handle.flush()
                os.fsync(handle.fileno())
            _replace_snapshot_with_retry(temp_path, target)
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    return write_snapshot


def _snapshot_target(snapshot_path: str, *, artifact_root: str) -> Path:
    root_text = str(artifact_root or "").strip()
    if not root_text:
        raise ValueError("snapshot_path requires ui_state.artifact_folder so the write target is bounded.")
    root = Path(root_text).expanduser().resolve(strict=False)
    candidate = Path(snapshot_path).expanduser()
    target = candidate.resolve(strict=False) if candidate.is_absolute() else (root / candidate).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("snapshot_path must stay inside ui_state.artifact_folder.") from exc
    if target == root:
        raise ValueError("snapshot_path must point to a file inside ui_state.artifact_folder.")
    return target


def _error_cases_root(artifact_root: str) -> Path | None:
    text = str(artifact_root or "").strip()
    if not text:
        return None
    return Path(text).expanduser().resolve(strict=False) / "Error Cases"


def _error_cases_folder_snapshot(path: Path) -> dict[str, Any]:
    files: list[Path] = []
    try:
        if path.exists():
            files = _error_case_original_files(path)
    except OSError as exc:
        return {"path": str(path), "exists": path.exists(), "file_count": 0, "scan_error": str(exc)}
    latest = sorted(files, key=lambda item: item.stat().st_mtime if item.exists() else 0, reverse=True)[:5]
    return {
        "path": str(path),
        "exists": path.exists(),
        "file_count": len(files),
        "latest_files": [item.name for item in latest],
    }


def _error_case_original_files(error_root: Path) -> list[Path]:
    originals_dirs = [path for path in error_root.rglob("originals") if path.is_dir()]
    files: set[Path] = set()
    for originals_dir in originals_dirs:
        for item in originals_dir.rglob("*"):
            if item.is_file():
                files.add(item)
    return sorted(files)


def _replace_snapshot_with_retry(temp_path: Path, target: Path) -> None:
    for attempt in range(SNAPSHOT_REPLACE_ATTEMPTS):
        try:
            os.replace(temp_path, target)
            _fsync_parent(target.parent)
            return
        except OSError as exc:
            if attempt == SNAPSHOT_REPLACE_ATTEMPTS - 1 or not _is_retryable_snapshot_replace_error(exc):
                raise
            time.sleep(SNAPSHOT_REPLACE_RETRY_SECONDS * (attempt + 1))


def _is_retryable_snapshot_replace_error(exc: OSError) -> bool:
    winerror = getattr(exc, "winerror", None)
    if isinstance(winerror, int):
        return winerror in SNAPSHOT_TRANSIENT_WINERRORS
    return isinstance(exc, PermissionError)


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
