"""Lifecycle workflow for generic orchestrator-owned debug sessions."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from ..bootstrap import STATE_ROOT
from . import launcher, launch_validation, payloads, polling, process_lifecycle, registry, session_repository, steps
from .types import DebugResult, DebugSession, DebugSessionRequest, DebugSnapshot, TERMINAL_STATUSES


def start(
    module_key: str,
    mode: str,
    input_root: Path | str,
    *,
    source_path: str = "",
    state_root: Path | None = None,
    registry_path: Path | None = None,
    options: dict | None = None,
    session_id: str | None = None,
    descriptor=None,
    plan=None,
    modules=None,
) -> DebugSession:
    normalized_module_key = str(module_key or "").strip()
    normalized_mode = str(mode or "").strip().lower()
    normalized_source_path = str(source_path or "").strip()
    normalized_input_root = Path(input_root)
    launch_validation.validate_launch_request(
        normalized_module_key,
        normalized_mode,
        normalized_input_root,
        normalized_source_path,
    )
    descriptor = descriptor or registry.descriptor_for(module_key, registry_path=registry_path)
    plan = plan or registry.plan_for(module_key, mode, registry_path=registry_path)
    session_root = Path(state_root or STATE_ROOT) / "debug_sessions" / (session_id or _session_id()) / module_key
    request = DebugSessionRequest(
        session_id=session_root.parent.name,
        module_key=normalized_module_key,
        mode=normalized_mode,
        input_root=normalized_input_root,
        source_path=normalized_source_path,
        output_root=session_root / "outputs",
        session_root=session_root,
        options=dict(options or {}),
    )
    session = DebugSession(request=request, descriptor=descriptor, plan=plan, registry_path=registry_path)
    session.active_step = plan.steps[0] if plan.steps else None
    session.output_root.mkdir(parents=True, exist_ok=True)
    session.home_path.mkdir(parents=True, exist_ok=True)
    session_repository.prune_sessions(state_root=state_root, protected_session_id=session.request.session_id)
    return _start_step(session, modules=modules)


def refresh(session: DebugSession, *, modules=None) -> DebugSession:
    if session.active_step is None:
        return session
    session.snapshot = polling.load_snapshot(session.snapshot_path, fallback_stage=_stage_name(session), fallback_status="running")
    session.result = polling.load_result(session.result_path)
    if not _step_finished(session):
        return session
    if session.result is None:
        session.result = polling.write_result(
            session.result_path,
            DebugResult(status="error", summary="Step failed", error=_missing_result_error(session)),
        )
    while session.result is not None and session.result.status in TERMINAL_STATUSES:
        session.completed_results.append(session.result)
        _stop_process(session, reason="debug step completed")
        if session.result.status != "ok":
            return finish(session)
        if session.current_step_index + 1 >= len(session.plan.steps):
            return finish(session)
        session.current_step_index += 1
        session.active_step = session.plan.steps[session.current_step_index]
        session.process_handle = None
        session.result = None
        session.snapshot = None
        _start_step(session, modules=modules)
        session.snapshot = polling.load_snapshot(session.snapshot_path, fallback_stage=_stage_name(session), fallback_status="running")
        session.result = polling.load_result(session.result_path)
        if not _step_finished(session):
            return session
        if session.result is None:
            session.result = polling.write_result(
                session.result_path,
                DebugResult(status="error", summary="Step failed", error=_missing_result_error(session)),
            )
    return session


def cancel(session: DebugSession) -> DebugSession:
    session.cancel_path.parent.mkdir(parents=True, exist_ok=True)
    session.cancel_path.touch(exist_ok=True)
    snapshot = polling.load_snapshot(session.snapshot_path, fallback_stage=_stage_name(session), fallback_status="cancelling")
    if snapshot.status not in TERMINAL_STATUSES:
        snapshot.status = "cancelling"
        session.snapshot = polling.write_snapshot(session.snapshot_path, snapshot)
    _stop_process(session, reason="debug session cancelled")
    return session


def finish(session: DebugSession) -> DebugSession:
    _stop_process(session, reason="debug session finished")
    session.process_handle = None
    session.active_step = None
    session.snapshot = polling.load_snapshot(
        session.snapshot_path,
        fallback_stage=session.descriptor.stage_role,
        fallback_status="pending",
    )
    session.result = session.result or polling.load_result(session.result_path)
    aggregated = payloads.aggregate_result(_terminal_results(session))
    if aggregated is not None:
        session.result = aggregated
    return session


def _start_step(session: DebugSession, *, modules) -> DebugSession:
    if session.active_step is None:
        return session
    _clear_step_files(session)
    if session.active_step.kind == "module_step":
        return _start_module_step(session, modules=modules)
    return _run_host_step(session, modules=modules)


def _start_module_step(session: DebugSession, *, modules) -> DebugSession:
    step = session.active_step
    spec = registry.module_runtime(step.module_key, registry_path=session.registry_path, required_actions=(step.action,))
    session_home_env = registry.session_home_env(step.module_key)
    payload = payloads.build_module_payload(session, modules=modules)
    polling.write_json(session.request_path, payload)
    session.process_handle = launcher.launch_process(
        spec,
        payload,
        request_path=session.request_path,
        response_path=session.response_path,
        env_overlay=steps.module_env_overlay(
            session,
            modules,
            overlay_key=session_home_env,
            module_key=step.module_key,
        ),
        bootstrap_home=session.home_path if session_home_env else None,
    )
    session.snapshot = polling.write_snapshot(
        session.snapshot_path,
        DebugSnapshot(status="running", stage=_stage_name(session), detail=_step_detail(session)),
    )
    return session


def _run_host_step(session: DebugSession, *, modules) -> DebugSession:
    return steps.run_host_step(session, modules=modules, stage_name_fn=_stage_name, step_detail_fn=_step_detail)


def _step_finished(session: DebugSession) -> bool:
    exit_code = polling.process_exit_code(session.process_handle)
    if exit_code is None:
        return session.result is not None and session.result.status in TERMINAL_STATUSES
    return True


def _missing_result_error(session: DebugSession) -> str:
    exit_code = polling.process_exit_code(session.process_handle)
    return f"{_stage_name(session)} ended without result.json (exit code {exit_code})."


def _stage_name(session: DebugSession) -> str:
    if session.active_step is not None and session.active_step.kind == "host_step":
        return "Request Enrichment"
    return session.descriptor.stage_role


def _step_detail(session: DebugSession) -> str:
    return session.request.logical_source_path or session.request.mode


def _clear_step_files(session: DebugSession) -> None:
    for path in (session.request_path, session.response_path, session.result_path, session.snapshot_path):
        path.unlink(missing_ok=True)


def _terminal_results(session: DebugSession) -> list[DebugResult]:
    results = list(session.completed_results)
    if session.result is not None and (not results or results[-1] is not session.result):
        results.append(session.result)
    return results


def _session_id() -> str:
    return f"dbg_{uuid4().hex[:12]}"


def _stop_process(session: DebugSession, *, reason: str) -> None:
    process_lifecycle.stop_session_process(session, reason=reason)
