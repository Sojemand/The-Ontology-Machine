from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import traceback
from typing import Any, Mapping

from .semantic_control_kernel_client import (
    UNAVAILABLE_SAFE_MESSAGE,
    SemanticControlKernelClient,
)

_BRIDGE_LOG_MAX_BYTES = 5 * 1024 * 1024
_BRIDGE_LOG_BACKUP_COUNT = 3


def kernel_list_client_frontend_events(request: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return _client().list_client_frontend_events(request)
    except Exception as exc:
        _log_bridge_exception("list_client_frontend_events", exc, request)
        return {
            "schema_version": "kernel.client_frontend_event_batch.v1",
            "cursor": str(request.get("cursor") or "0"),
            "events": [],
        }


def kernel_submit_user_interaction_response(request: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return _client().submit_user_interaction_response(request)
    except Exception as exc:
        _log_bridge_exception("submit_user_interaction_response", exc, request)
        return _host_bridge_unavailable_response(request, exc)


def kernel_cancel_user_interaction(request: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return _client().cancel_user_interaction(request)
    except Exception as exc:
        _log_bridge_exception("cancel_user_interaction", exc, request)
        return _host_bridge_unavailable_response(request, exc)


def kernel_list_event_scoped_tool_definitions(request: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return _client().list_event_scoped_tool_definitions(request)
    except Exception as exc:
        _log_bridge_exception("list_event_scoped_tool_definitions", exc, request)
        return {
            "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
            "mirror_event_id": str(request.get("mirror_event_id") or ""),
            "recovery_event_id": str(request.get("recovery_event_id") or ""),
            "state_snapshot_id": str(request.get("state_snapshot_id") or ""),
            "status": "failed",
            "tool_definitions": [],
            "error": {
                "code": "semantic_control_kernel_unavailable",
                "safe_message": UNAVAILABLE_SAFE_MESSAGE,
                "detail": _safe_error_detail(exc),
            },
        }


def _client() -> SemanticControlKernelClient:
    return SemanticControlKernelClient()


def _host_bridge_unavailable_response(request: Mapping[str, Any], exc: Exception | None = None) -> dict[str, Any]:
    return {
        "schema_version": "semantic_control_kernel.host_bridge_response.v1",
        "status": "failed",
        "interaction_request_id": str(request.get("interaction_request_id") or ""),
        "user_visible_summary": UNAVAILABLE_SAFE_MESSAGE,
        "error": {
            "code": "semantic_control_kernel_unavailable",
            "safe_message": UNAVAILABLE_SAFE_MESSAGE,
            "detail": _safe_error_detail(exc),
        },
    }


def _log_bridge_exception(action: str, exc: Exception, request: Mapping[str, Any]) -> None:
    log_path = _bridge_log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        request_ref = _safe_log_text(str(
            request.get("interaction_request_id")
            or request.get("client_request_id")
            or request.get("mirror_event_id")
            or request.get("cursor")
            or ""
        ))
        lines = [
            f"[{timestamp}] action={action} request_ref={request_ref}",
            f"exception={type(exc).__name__}: {_safe_log_text(str(exc))}",
            _safe_log_text(traceback.format_exc().rstrip()),
            "",
        ]
        _append_bridge_log(log_path, "\n".join(lines))
    except Exception:
        pass


def _append_bridge_log(log_path: Path, text: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _rotate_bridge_log(log_path, incoming_bytes=len(text.encode("utf-8")))
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _rotate_bridge_log(log_path: Path, *, incoming_bytes: int) -> None:
    try:
        size = log_path.stat().st_size
    except FileNotFoundError:
        return
    except OSError:
        return
    if size + incoming_bytes <= _BRIDGE_LOG_MAX_BYTES:
        return
    if _BRIDGE_LOG_BACKUP_COUNT <= 0:
        try:
            log_path.unlink(missing_ok=True)
        except OSError:
            pass
        return

    try:
        _bridge_backup_path(log_path, _BRIDGE_LOG_BACKUP_COUNT).unlink(missing_ok=True)
        for index in range(_BRIDGE_LOG_BACKUP_COUNT - 1, 0, -1):
            source = _bridge_backup_path(log_path, index)
            if source.exists():
                source.replace(_bridge_backup_path(log_path, index + 1))
        if log_path.exists():
            log_path.replace(_bridge_backup_path(log_path, 1))
    except OSError:
        pass


def _bridge_backup_path(log_path: Path, index: int) -> Path:
    return log_path.with_name(f"{log_path.name}.{index}")


def _bridge_log_path() -> Path:
    return Path(__file__).resolve().parents[1] / "state" / "semantic_control_kernel_host_bridge.log"


def _safe_error_detail(exc: Exception | None) -> str:
    if exc is None:
        return ""
    detail = str(exc)
    if not detail:
        return type(exc).__name__
    return _safe_log_text(detail)


def _safe_log_text(detail: str) -> str:
    detail = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted-secret]", detail)
    legacy_tool_name = "inspect" + "_" + "workflow"
    detail = detail.replace(legacy_tool_name, "[redacted-tool]")
    return detail
