from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from semantic_control_kernel.repository.atomic_json_io import atomic_write_text, stable_json_dumps


STATE_LAYOUT_VERSION = "phase3.v1"
STATE_ROOT_MANIFEST_SCHEMA_VERSION = "repository.state_root_manifest.v1"

STATE_LAYOUT_DIRS: tuple[str, ...] = (
    ".tmp",
    ".fs_locks",
    "workflow_runs/active",
    "workflow_runs/history",
    "resume",
    "pending_confirmations/active",
    "pending_confirmations/history",
    "pending_interactions/active",
    "pending_interactions/history",
    "locks/active",
    "locks/history",
    "receipts/confirmations",
    "receipts/operations",
    "receipts/recoveries",
    "receipts/index/by_workflow",
    "receipts/index/by_target",
    "events/progress",
    "events/mirror",
    "events/recovery",
    "events/tool_availability",
    "attach_states/by_database",
    "attach_states/history",
    "artifact_trees/active",
    "artifact_trees/history",
    "bindings/records",
    "bindings/index/by_database_path",
    "bindings/index/by_artifact_root",
    "bindings/history",
    "adapter_calls",
    "debug/traces",
    "debug/adapter_calls",
    "debug/background_continuations",
    "debug/llm_attempts",
    "debug/redaction_reports",
    "support/bundles",
    "support/cleanup_history",
    "archive/resets",
    "quarantine/corrupt",
    "quarantine/partial_writes",
)

STATE_README_TEXT = """# Semantic Control Kernel State

This directory is module-local mutable Kernel state. Owner module databases,
Artifact Trees, Semantic Release packages, source documents, Pipeline batch
artifacts, MCP Server state and Client Frontend state do not live here.
"""

_ENSURED_LAYOUT_ROOTS: set[str] = set()


def _path_key(path: str | os.PathLike[str]) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    atomic_write_text(path, stable_json_dumps(payload))


def _write_text(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def _is_relative_safe(parts: Iterable[str]) -> bool:
    for part in parts:
        path = Path(part)
        if path.is_absolute() or part in {"", ".", ".."} or ".." in path.parts:
            return False
    return True
