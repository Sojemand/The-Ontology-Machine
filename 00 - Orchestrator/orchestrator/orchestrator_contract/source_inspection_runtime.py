"""Runtime and filesystem helpers for source sample inspection."""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

from ..debug_host import polling as debug_polling
from ..debug_host import workflow as debug_workflow
from ..pipeline.path_budget import WINDOWS_PATH_BUDGET, budgeted_name


def source_inspection_modules(root: Path):
    from ..integrations.workflow import SubmodulePipelineModules

    return SubmodulePipelineModules(state_dir=root / "state")


def wait_for_debug_session(session, *, timeout_seconds: int, modules=None):
    deadline = time.monotonic() + timeout_seconds
    while session.active_step is not None:
        if time.monotonic() > deadline:
            debug_workflow.cancel(session)
            raise TimeoutError(f"Document inspection timed out after {timeout_seconds} seconds.")
        session = debug_workflow.refresh(session, modules=modules)
        if session.active_step is not None:
            time.sleep(0.2)
    return session


def cleanup_old_inspections(base: Path, *, older_than_days: int) -> None:
    if older_than_days < 0 or not base.exists():
        return
    cutoff = time.time() - (older_than_days * 24 * 60 * 60)
    base_resolved = base.resolve()
    for child in base.iterdir():
        try:
            child_resolved = child.resolve()
            child_resolved.relative_to(base_resolved)
        except (OSError, ValueError):
            continue
        if child_resolved == base_resolved:
            continue
        try:
            if child.stat().st_mtime <= cutoff:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink(missing_ok=True)
        except OSError:
            continue


def safe_inspection_filename(name: str, *, parent: Path | None = None) -> str:
    original = Path(str(name or "sample")).name.strip() or "sample"
    stem = Path(original).stem
    suffix = Path(original).suffix
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "sample"
    safe_suffix = suffix if re.fullmatch(r"\.[A-Za-z0-9]+", suffix or "") else ""
    candidate = f"{safe_stem}{safe_suffix}"
    if parent is None or len(str(Path(parent) / candidate)) <= WINDOWS_PATH_BUDGET:
        return candidate
    fallback = budgeted_name(Path(parent), candidate)
    if len(str(Path(parent) / fallback)) <= WINDOWS_PATH_BUDGET:
        return fallback
    raise ValueError(f"Source inspection path is too deep for Windows path budget: {parent}")


def resolved_outputs(session_root: Path, values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        path = debug_polling.resolve_output_path(session_root, value)
        if path not in paths:
            paths.append(path)
    return paths


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
