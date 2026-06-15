"""Merge action flow for owner-provided operation cards."""
from __future__ import annotations

from pathlib import Path

from ..repository import atomic_json_write
from .. import validation
from . import operation_results


def resolve_merge_interaction(app, surface_id: str, choice_id: str, *, runtime) -> None:
    state = app._operation_results.get(surface_id)
    merge_flow = state.get("merge_flow") if isinstance(state, dict) else None
    interaction = current_merge_interaction(app, surface_id)
    if not isinstance(merge_flow, dict) or not isinstance(interaction, dict):
        return
    choice = _find_choice(interaction, choice_id)
    if not isinstance(choice, dict):
        return
    decision = choice.get("decision")
    if decision in (None, ""):
        response = {
            "status": "cancelled",
            "headline": "Corpus merge cancelled",
            "summary_lines": ["The merge was cancelled before mutation."],
            "artifacts": operation_results.merge_flow_artifacts(merge_flow),
        }
        runtime.remember_result(app, surface_id, merge_flow["action_link"], response)
        return runtime.rerender(app)
    argument_name = str(interaction.get("artifact_argument_name") or "").strip()
    artifact_path = write_merge_artifact(app, surface_id, interaction, decision)
    merge_flow.setdefault("artifact_paths", {})[argument_name] = str(artifact_path)
    merge_flow["pending_index"] = int(merge_flow.get("pending_index") or 0) + 1
    pending = merge_flow.get("pending_interactions") if isinstance(merge_flow.get("pending_interactions"), list) else []
    if int(merge_flow.get("pending_index") or 0) < len(pending):
        app._operation_results[surface_id] = state
        return runtime.rerender(app)
    start_merge_execution(app, surface_id, merge_flow, runtime=runtime)


def current_merge_interaction(app, surface_id: str) -> dict | None:
    state = app._operation_results.get(surface_id)
    merge_flow = state.get("merge_flow") if isinstance(state, dict) else None
    return operation_results.pending_interaction_from_flow(merge_flow) if isinstance(merge_flow, dict) else None


def merge_interaction_choices(app, surface_id: str) -> tuple[dict, ...]:
    interaction = current_merge_interaction(app, surface_id)
    choices = interaction.get("choices") if isinstance(interaction, dict) else None
    if not isinstance(choices, list):
        return ()
    return tuple(choice for choice in choices if isinstance(choice, dict) and str(choice.get("choice_id") or "").strip())


def start_merge_flow(app, surface_id: str, action_link: dict, payload: dict, *, runtime) -> None:
    preflight_payload = {key: value for key, value in payload.items() if key != "action"}
    preflight_payload["action"] = "merge_preflight"
    runtime.action_loading(app).add(surface_id)
    token_name = f"operation:{surface_id}"
    token = runtime.background_jobs.next_token(app, token_name)
    if runtime.has_async_ui(app):
        runtime.rerender(app)
    runtime.background_jobs.start(
        app,
        work=lambda: runtime.invoke_module_contract(
            module_root=Path(app._selected_entry().module_root),
            contract_module=str(action_link.get("contract_module") or ""),
            state_root=app._state_root,
            payload=preflight_payload,
        ),
        deliver=lambda result, error: finish_merge_preflight(app, surface_id, action_link, token_name, token, payload, result, error, runtime=runtime),
    )


def finish_merge_preflight(app, surface_id: str, action_link: dict, token_name: str, token: int, merge_payload: dict, result, error: Exception | None, *, runtime) -> None:
    if not runtime.background_jobs.is_current(app, token_name, token):
        return
    runtime.action_loading(app).discard(surface_id)
    if error is not None:
        runtime.remember_result(app, surface_id, action_link, {"status": "error", "reason": str(error)})
        return runtime.rerender(app)
    response = result if isinstance(result, dict) else {"status": "error", "reason": "Invalid action response."}
    detail = response.get("detail") if isinstance(response.get("detail"), dict) else {}
    pending = detail.get("pending_interactions") if isinstance(detail, dict) else None
    if response.get("status") != "ok" or not isinstance(detail, dict) or bool(detail.get("blocked")):
        runtime.remember_result(app, surface_id, action_link, response)
        return runtime.rerender(app)
    merge_flow = {"action_link": dict(action_link), "base_payload": dict(merge_payload), "pending_interactions": pending or [], "pending_index": 0, "artifact_paths": {}}
    if isinstance(pending, list) and pending:
        runtime.remember_result(app, surface_id, action_link, response, merge_flow=merge_flow)
        return runtime.rerender(app)
    start_merge_execution(app, surface_id, merge_flow, runtime=runtime)


def start_merge_execution(app, surface_id: str, merge_flow: dict, *, runtime) -> None:
    action_link = merge_flow["action_link"]
    payload = dict(merge_flow.get("base_payload") or {})
    payload["action"] = "merge_corpus_databases"
    artifacts = merge_flow.get("artifact_paths")
    if isinstance(artifacts, dict):
        payload.update({key: value for key, value in artifacts.items() if value})
    if surface_id in runtime.action_loading(app):
        return
    runtime.action_loading(app).add(surface_id)
    token_name = f"operation:{surface_id}"
    token = runtime.background_jobs.next_token(app, token_name)
    if runtime.has_async_ui(app):
        runtime.rerender(app)
    runtime.background_jobs.start(
        app,
        work=lambda: runtime.invoke_module_contract(
            module_root=Path(app._selected_entry().module_root),
            contract_module=str(action_link.get("contract_module") or ""),
            state_root=app._state_root,
            payload=payload,
        ),
        deliver=lambda result, error: finish_merge_execution(app, surface_id, action_link, token_name, token, merge_flow, result, error, runtime=runtime),
    )


def finish_merge_execution(app, surface_id: str, action_link: dict, token_name: str, token: int, merge_flow: dict, result, error: Exception | None, *, runtime) -> None:
    if not runtime.background_jobs.is_current(app, token_name, token):
        return
    runtime.action_loading(app).discard(surface_id)
    if error is not None:
        response = {"status": "error", "reason": str(error), "artifacts": operation_results.merge_flow_artifacts(merge_flow)}
    else:
        response = result if isinstance(result, dict) else {"status": "error", "reason": "Invalid action response."}
        response = with_merge_artifacts(response, merge_flow)
    runtime.remember_result(app, surface_id, action_link, response)
    runtime.rerender(app)


def write_merge_artifact(app, surface_id: str, interaction: dict, decision: str) -> Path:
    artifact_dir = validation.ensure_state_child(app._state_root, app._state_root / "merge-confirmations" / _safe_name(app._selected_module) / _safe_name(surface_id))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    filename = validation.safe_filename(str(interaction.get("recommended_filename") or ""), fallback="merge-confirmation.json")
    artifact_path = validation.ensure_state_child(app._state_root, artifact_dir / filename)
    payload = dict(interaction.get("artifact_template") or {})
    payload["decision"] = decision
    atomic_json_write(artifact_path, payload)
    return artifact_path


def with_merge_artifacts(response: dict, merge_flow: dict) -> dict:
    enriched = dict(response)
    enriched["artifacts"] = list(response.get("artifacts") or []) + operation_results.merge_flow_artifacts(merge_flow)
    return enriched


def _find_choice(interaction: dict, choice_id: str) -> dict | None:
    choices = interaction.get("choices")
    if not isinstance(choices, list):
        return None
    for choice in choices:
        if isinstance(choice, dict) and str(choice.get("choice_id") or "").strip() == choice_id:
            return choice
    return None


def _safe_name(value: str) -> str:
    safe = value.replace("/", ".").replace("\\", ".").replace(" ", "_")
    for char in ':*?"<>|':
        safe = safe.replace(char, "_")
    return validation.safe_filename(safe, fallback="segment")
