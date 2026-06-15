"""Preflight health and semantic-release workflow for orchestrator runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..integrations import ModuleHealthStatus, stage_name_for_module
from ..state import atomic_json_write
from . import debug, health_profile_policy, release_workflow, storage_repository


def run_preflight_healthcheck(
    engine: Any,
    *,
    module_keys: tuple[str, ...],
    scope: str,
    records: list[Any] | None = None,
    ui_state: Any | None = None,
) -> list[ModuleHealthStatus]:
    if not module_keys:
        return []
    required_dependencies_by_module = health_profile_policy.build_required_dependencies_by_module(records or [], scope=scope)
    for module_key in module_keys:
        stage_name = stage_name_for_module(module_key)
        if stage_name:
            debug.set_stage(engine, stage_name, "Checking...", "Pre-start check")
    debug.emit_snapshot(engine)
    results = engine._modules.healthcheck(
        module_keys=module_keys,
        scope=scope,
        required_dependencies_by_module=required_dependencies_by_module or None,
        corpus_db_path=storage_repository.corpus_db_path(ui_state) if ui_state is not None else None,
    )
    blocking_issues: list[str] = []
    stage_messages: dict[str, list[str]] = {}
    for result in results:
        for detail in result.optional_issues():
            debug.append_log(engine, f"[HEALTH-WARN] {result.display_name}: {detail}")
        issues = result.blocking_issues()
        if not issues:
            stage_name = stage_name_for_module(result.key)
            if stage_name:
                debug.set_stage(engine, stage_name, "Ready", "Healthcheck ok")
            continue
        detail = "; ".join(issues)
        stage_name = stage_name_for_module(result.key)
        if stage_name:
            stage_messages.setdefault(stage_name, []).append(f"{result.display_name}: {detail}")
        blocking_issues.append(f"{result.display_name}: {detail}")
    for stage_name, messages in stage_messages.items():
        debug.set_stage(engine, stage_name, "Error", " | ".join(messages))
    if blocking_issues:
        message = "Healthcheck failed: " + " | ".join(blocking_issues)
        artifact_path = _write_healthcheck_failure_artifact(
            engine,
            scope=scope,
            results=results,
            required_dependencies_by_module=required_dependencies_by_module,
        )
        debug.append_log(engine, f"[HEALTH-ERROR] {message}")
        if artifact_path is not None:
            debug.append_log(engine, f"[HEALTH-ARTIFACT] {artifact_path}")
        debug.emit_snapshot(engine)
        raise RuntimeError(message)
    debug.emit_snapshot(engine)
    return results


def activate_selected_release(engine: Any, ui_state) -> None:
    release_workflow.run_release_activation(engine, ui_state)


def _annotated_release_failure(detail: str, release_path: Path) -> str:
    message = str(detail).strip() or "Semantic Release could not be activated."
    if "release_path=" in message:
        return message
    return f"{message} [release_path={release_path}]"


def _write_healthcheck_failure_artifact(
    engine: Any,
    *,
    scope: str,
    results: list[ModuleHealthStatus],
    required_dependencies_by_module: dict[str, tuple[str, ...]] | None,
) -> Path | None:
    active_log_path = getattr(engine, "_active_log_path", None)
    if active_log_path is None:
        return None
    artifact_path = Path(active_log_path).parent / "healthcheck.failure.json"
    payload = {
        "scope": scope,
        "required_dependencies_by_module": {
            str(module_key): list(dependencies)
            for module_key, dependencies in (required_dependencies_by_module or {}).items()
        },
        "results": [
            {
                "key": result.key,
                "display_name": result.display_name,
                "healthy": result.healthy,
                "message": result.message,
                "dependencies": [
                    {
                        "name": dependency.name,
                        "kind": dependency.kind,
                        "required": dependency.required,
                        "healthy": dependency.healthy,
                        "detail": dependency.detail,
                    }
                    for dependency in result.dependencies
                ],
            }
            for result in results
        ],
    }
    atomic_json_write(artifact_path, payload)
    return artifact_path
