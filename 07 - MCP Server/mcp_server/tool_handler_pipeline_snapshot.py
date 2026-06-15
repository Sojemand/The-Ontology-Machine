from __future__ import annotations

from pathlib import Path
from typing import Any

from .contract_client import module_spec
from .tool_handler_pipeline_context import _is_within, _record_artifact_paths, _record_matches_active_workspace
from .tool_handler_pipeline_store import _read_json_file, _tail_text

def _compact_pipeline_snapshot(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    stage_payload = payload.get("stage_statuses")
    stage_statuses: dict[str, dict[str, Any]] = {}
    if isinstance(stage_payload, dict):
        for name, stage in stage_payload.items():
            if not isinstance(stage, dict):
                continue
            stage_statuses[str(name)] = {
                "status": str(stage.get("status") or ""),
                "detail": str(stage.get("detail") or "")[:300],
                "progress_current": _safe_int(stage.get("progress_current")),
                "progress_total": _safe_int(stage.get("progress_total")),
                "progress_label": str(stage.get("progress_label") or "")[:80],
            }
    return {
        "total": _safe_int(payload.get("total")),
        "completed": _safe_int(payload.get("completed")),
        "pending": _safe_int(payload.get("pending")),
        "success": _safe_int(payload.get("success")),
        "errors": _safe_int(payload.get("errors")),
        "needs_review": _safe_int(payload.get("needs_review")),
        "retries": _safe_int(payload.get("retries")),
        "current_file": str(payload.get("current_file") or "")[:300],
        "current_attempt": _safe_int(payload.get("current_attempt")),
        "current_route_family": str(payload.get("current_route_family") or "")[:120],
        "current_optimizer_module": str(payload.get("current_optimizer_module") or "")[:120],
        "current_interpreter_module": str(payload.get("current_interpreter_module") or "")[:120],
        "current_intake_reason": str(payload.get("current_intake_reason") or "")[:300],
        "is_running": bool(payload.get("is_running")),
        "aborted": bool(payload.get("aborted")),
        "stage_statuses": stage_statuses,
    }


def _preflight_failure_summary(response_payload: Any, latest_log: Path | None) -> dict[str, Any] | None:
    if not isinstance(response_payload, dict):
        return None
    reason = str(response_payload.get("reason") or response_payload.get("error") or "")
    if "Healthcheck fehlgeschlagen" not in reason:
        return None
    artifact_path = latest_log.parent / "healthcheck.failure.json" if latest_log is not None else None
    artifact = _read_json_file(artifact_path) if artifact_path is not None and artifact_path.exists() else None
    results = artifact.get("results") if isinstance(artifact, dict) else []
    modules: list[dict[str, Any]] = []
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            modules.append(
                {
                    "key": str(item.get("key") or ""),
                    "display_name": str(item.get("display_name") or item.get("key") or ""),
                    "healthy": bool(item.get("healthy")),
                    "message": str(item.get("message") or ""),
                    "blocking_dependencies": [
                        {
                            "name": str(dependency.get("name") or ""),
                            "detail": str(dependency.get("detail") or ""),
                        }
                        for dependency in item.get("dependencies", [])
                        if isinstance(dependency, dict)
                        and bool(dependency.get("required"))
                        and not bool(dependency.get("healthy"))
                    ],
                }
            )
    return {
        "reason": reason,
        "artifact_path": str(artifact_path) if artifact_path is not None and artifact_path.exists() else "",
        "scope": str(artifact.get("scope") or "") if isinstance(artifact, dict) else "",
        "modules": modules,
        "message": "Der Lauf ist im Vorstart-Check abgebrochen; Dokumentverarbeitung wurde nicht gestartet.",
    }


def _zero_document_run_summary(
    response_payload: Any,
    input_before_run: Any,
    snapshot_payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(response_payload, dict) or str(response_payload.get("status") or "") != "ok":
        return None
    input_total = _safe_int(input_before_run.get("total_files") if isinstance(input_before_run, dict) else None)
    if input_total <= 0:
        return None
    run_total = _safe_int(response_payload.get("total"))
    snapshot_total = _safe_int(snapshot_payload.get("total")) if isinstance(snapshot_payload, dict) else 0
    if run_total > 0 or snapshot_total > 0:
        return None
    preview_files = input_before_run.get("preview_files") if isinstance(input_before_run, dict) else []
    if not isinstance(preview_files, list):
        preview_files = []
    return {
        "input_files": input_total,
        "reported_total": run_total,
        "snapshot_total": snapshot_total,
        "preview_files": preview_files[:10],
        "message": (
            "Der Lauf wurde gestartet, aber der Orchestrator hat 0 Dokumente zur Verarbeitung uebernommen, "
            "obwohl im Input-Ordner Dateien lagen."
        ),
    }


def _safe_int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _pipeline_state_summary(active_context: dict[str, Any]) -> dict[str, Any]:
    state_path = module_spec("orchestrator").root / "state" / "pipeline" / "pipeline_state.json"
    payload = _read_json_file(state_path)
    documents = payload.get("documents") if isinstance(payload, dict) else {}
    if not isinstance(documents, dict):
        documents = {}
    input_root = Path(str(active_context.get("input_folder") or "")).expanduser().resolve()
    artifact_root = Path(str(active_context.get("artifact_folder") or "")).expanduser().resolve()
    by_status: dict[str, int] = {}
    by_final_disposition: dict[str, int] = {}
    active_records = 0
    outside_artifact_examples: list[dict[str, str]] = []
    for record in documents.values():
        if not isinstance(record, dict):
            continue
        if not _record_matches_active_workspace(record, input_root, artifact_root):
            continue
        active_records += 1
        status = str(record.get("status") or "unknown")
        final = str(record.get("final_disposition") or "pending")
        by_status[status] = by_status.get(status, 0) + 1
        by_final_disposition[final] = by_final_disposition.get(final, 0) + 1
        for path in _record_artifact_paths(record):
            resolved = path.expanduser().resolve()
            if str(artifact_root) and not _is_within(resolved, artifact_root):
                if len(outside_artifact_examples) < 5:
                    outside_artifact_examples.append(
                        {
                            "file_name": str(record.get("file_name") or ""),
                            "artifact_path": str(path),
                        }
                    )
                break
    return {
        "state_path": str(state_path),
        "total_records": len(documents),
        "active_workspace_records": active_records,
        "by_status": by_status,
        "by_final_disposition": by_final_disposition,
        "outside_artifact_examples": outside_artifact_examples,
    }

__all__ = [name for name in globals() if not name.startswith("__")]
