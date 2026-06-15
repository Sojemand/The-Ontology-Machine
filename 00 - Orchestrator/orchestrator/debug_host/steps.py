"""Step-level helpers for debug-host module and host execution."""

from __future__ import annotations

from ..integrations.workflow_helpers import env_overlay_for
from . import polling
from .request_enrichment_steps import build_request_outputs
from .types import DebugResult, DebugSnapshot

_REQUEST_ENRICHMENT_TARGETS = {
    "optimizer": "interpreter",
    "interpreter": "interpreter",
}
def module_env_overlay(session, modules, *, overlay_key: str, module_key: str) -> dict[str, str] | None:
    overlay: dict[str, str] = {}
    if overlay_key:
        overlay[overlay_key] = str(session.home_path)
    credentials_overlay = env_overlay_for(modules, module_key) if modules is not None else None
    if credentials_overlay:
        overlay.update(credentials_overlay)
    return overlay or None


def run_host_step(session, *, modules, stage_name_fn, step_detail_fn):
    prior = session.completed_results[-1] if session.completed_results else None
    request_payload = {"name": getattr(session.active_step, "name", "")}
    polling.write_json(session.request_path, request_payload)
    session.snapshot = polling.write_snapshot(
        session.snapshot_path,
        DebugSnapshot(status="running", stage=stage_name_fn(session), detail=step_detail_fn(session)),
    )
    if session.active_step is None or session.active_step.name != "request_enrichment":
        return _finish_host_step(
            session,
            stage_name_fn,
            {"status": "error", "error": "Unknown host_step"},
            DebugResult(status="error", summary="Host step failed", error="Unknown host_step"),
        )
    if modules is None or prior is None:
        return _finish_host_step(
            session,
            stage_name_fn,
            {"status": "error", "error": "Missing prerequisites"},
            DebugResult(status="error", summary="Host step failed", error="Missing prerequisites"),
        )
    try:
        module_key = _REQUEST_ENRICHMENT_TARGETS.get(session.request.module_key, "interpreter")
        request_outputs = build_request_outputs(session, modules=modules, prior=prior, module_key=module_key)
        payload = {
            "status": "ok",
            "request_count": len(request_outputs),
            "requests": list(request_outputs),
        }
        artifacts = {"interpreter_request": list(request_outputs)}
        outputs = {"interpreter_request": list(request_outputs)}
        result = DebugResult(
            status="ok",
            summary=_request_enrichment_summary(len(request_outputs)),
            artifacts=artifacts,
            outputs=outputs,
        )
        return _finish_host_step(session, stage_name_fn, payload, result)
    except Exception as exc:
        error = str(exc)
        return _finish_host_step(
            session,
            stage_name_fn,
            {"status": "error", "error": error},
            DebugResult(status="error", summary="Request Enrichment failed", error=error),
        )


def _finish_host_step(session, stage_name_fn, response: dict, result: DebugResult):
    polling.write_json(session.response_path, response)
    session.result = polling.write_result(session.result_path, result)
    session.snapshot = polling.write_snapshot(
        session.snapshot_path,
        DebugSnapshot(status=result.status, stage=stage_name_fn(session), detail=result.summary),
    )
    polling.append_log(session.run_log_path, f"[{result.status.upper()}] {result.summary or result.error}")
    return session
def _request_enrichment_summary(count: int) -> str:
    if count == 1:
        return "Request Enrichment completed"
    return f"Request Enrichment completed ({count} requests)"
