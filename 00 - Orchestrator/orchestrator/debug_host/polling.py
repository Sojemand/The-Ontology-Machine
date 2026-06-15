"""Filesystem polling helpers for generic debug-host sessions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import bounded_log
from ..state import atomic_json_write
from .types import DebugProcessHandle, DebugResult, DebugSnapshot, utc_now_iso

DEBUG_HOST_LOG_BYTES_HARD_CAP = 5 * 1024 * 1024


def load_snapshot(path: Path, *, fallback_stage: str = "", fallback_status: str = "pending") -> DebugSnapshot:
    payload = _load_json(path)
    if payload is None:
        return DebugSnapshot(status=fallback_status, stage=fallback_stage)
    return DebugSnapshot(
        status=str(payload.get("status", fallback_status)).strip() or fallback_status,
        stage=str(payload.get("stage", fallback_stage)).strip(),
        detail=str(payload.get("detail", "")).strip(),
        updated_at=str(payload.get("updated_at", "")).strip() or utc_now_iso(),
        processed=_coerce_int(payload.get("processed")),
        total=_coerce_int(payload.get("total")),
        warnings=_coerce_list(payload.get("warnings")),
        artifacts=_coerce_list(payload.get("artifacts")),
        counters=_coerce_int_mapping(payload.get("counters")),
    )


def load_result(path: Path) -> DebugResult | None:
    payload = _load_json(path)
    if payload is None:
        return None
    return DebugResult(
        status=str(payload.get("status", "error")).strip() or "error",
        summary=str(payload.get("summary", "")).strip(),
        artifacts=_coerce_list_mapping(payload.get("artifacts")),
        error=str(payload.get("error", "")).strip(),
        metrics=dict(payload.get("metrics", {})) if isinstance(payload.get("metrics"), dict) else {},
        outputs=_coerce_list_mapping(payload.get("outputs")),
    )


def load_log(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def process_exit_code(handle: DebugProcessHandle | None) -> int | None:
    if handle is None:
        return 0
    try:
        return handle.process.poll()
    except Exception:
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def snapshot_payload(snapshot: DebugSnapshot) -> dict[str, Any]:
    return {
        "status": snapshot.status,
        "stage": snapshot.stage,
        "detail": snapshot.detail,
        "updated_at": snapshot.updated_at,
        "processed": int(snapshot.processed),
        "total": int(snapshot.total),
        "warnings": list(snapshot.warnings),
        "artifacts": list(snapshot.artifacts),
        "counters": dict(snapshot.counters),
    }


def result_payload(result: DebugResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "summary": result.summary,
        "artifacts": _coerce_list_mapping(result.artifacts),
        "error": result.error,
        "metrics": dict(result.metrics),
        "outputs": _coerce_list_mapping(result.outputs),
    }


def write_snapshot(path: Path, snapshot: DebugSnapshot) -> DebugSnapshot:
    snapshot.updated_at = utc_now_iso()
    write_json(path, snapshot_payload(snapshot))
    return snapshot


def write_result(path: Path, result: DebugResult) -> DebugResult:
    write_json(path, result_payload(result))
    return result


def append_log(path: Path, line: str) -> None:
    bounded_log.append_text(path, f"{utc_now_iso()} {line}\n", max_bytes=DEBUG_HOST_LOG_BYTES_HARD_CAP)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_json_write(path, payload, indent=None)


def resolve_output_path(root: Path, value: str) -> Path:
    path = Path(str(value or ""))
    return path if path.is_absolute() else (root / path)


def relative_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _coerce_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _coerce_list(value: Any) -> list[str]:
    return [str(item) for item in value if str(item).strip()] if isinstance(value, list) else []


def _coerce_int_mapping(value: Any) -> dict[str, int]:
    return {str(key): _coerce_int(item) for key, item in value.items() if str(key).strip()} if isinstance(value, dict) else {}


def _coerce_list_mapping(value: Any) -> dict[str, list[str]]:
    return {str(key): _coerce_list(items) for key, items in value.items() if str(key).strip()} if isinstance(value, dict) else {}
