"""Workflow helpers for the orchestrator subprocess contract."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..profile_policy import payload_profile
from . import debug_processing, debug_support
from .types import DEBUG_RUN_ACTION, GENERATE_LLM_ACTION, HEALTHCHECK_ACTION, INTERPRET_DOCUMENT_ACTION


def error_response(message: str, *, debug_bundle_path: str = "") -> dict:
    payload = {"status": "error", "error": message}
    if debug_bundle_path:
        payload["debug_bundle_path"] = debug_bundle_path
    return payload


def interpret_document(
    payload: dict,
    *,
    load_dotenv_fn,
    load_config_fn,
    parse_interpret_document_command_fn,
    load_request_payload_fn,
    process_single_fn,
) -> dict:
    try:
        command = parse_interpret_document_command_fn(payload)
    except ValueError as exc:
        return error_response(str(exc))
    load_dotenv_fn()
    config = _build_effective_config(load_config_fn(), command.runtime_settings)
    config.interpreter_profile = payload_profile(payload)
    if command.debug_bundle_dir is not None:
        config.debug_bundle_dir = command.debug_bundle_dir
    try:
        request_input = load_request_payload_fn(command.request_path)
    except Exception as exc:
        return error_response(f"load_request: {exc}")
    result = process_single_fn(request_input, command.structured_output_path, config)
    if result.get("status") == "error":
        return error_response(
            str(result.get("error", "Interpreter-Fehler")),
            debug_bundle_path=str(result.get("debug_bundle_path") or ""),
        )
    response = {
        "status": str(result.get("status", "ok")),
        "structured_path": str(result.get("output_path") or ""),
        "needs_review": bool(result.get("needs_review", False)),
        "review_reason": str(result.get("review_reason", "")),
    }
    debug_bundle_path = str(result.get("debug_bundle_path") or "")
    if debug_bundle_path:
        response["debug_bundle_path"] = debug_bundle_path
    return response


def healthcheck(
    payload: dict,
    *,
    load_dotenv_fn,
    load_config_fn,
    parse_healthcheck_command_fn,
    create_provider_fn,
) -> dict:
    try:
        command = parse_healthcheck_command_fn(payload)
    except ValueError as exc:
        return error_response(str(exc))
    load_dotenv_fn()
    config = _build_effective_config(load_config_fn(), command.runtime_settings)
    config.interpreter_profile = payload_profile(payload)
    detail = _runtime_detail(config)
    try:
        provider = create_provider_fn(
            config.model,
            timeout=min(config.timeout_seconds, 15),
            base_url=config.api_base_url,
        )
        provider.check_ready()
    except Exception as exc:
        return _dependency_error(detail=f"{detail}: {exc}")
    return {
        "status": "ok",
        "healthy": True,
        "message": "",
        "dependencies": [_dependency_payload(healthy=True, detail=detail)],
    }


def debug_run(
    payload: dict,
    *,
    load_dotenv_fn,
    load_config_fn,
    parse_debug_run_command_fn,
    load_request_payload_fn,
    process_single_fn,
    process_batch_fn,
) -> dict:
    return _run_debug_action(
        payload,
        lambda: debug_processing.debug_run(
            payload,
            load_dotenv_fn=load_dotenv_fn,
            load_config_fn=load_config_fn,
            parse_debug_run_command_fn=parse_debug_run_command_fn,
            load_request_payload_fn=load_request_payload_fn,
            process_single_fn=process_single_fn,
            process_batch_fn=process_batch_fn,
        ),
        summary="Debuglauf fehlgeschlagen",
    )


def dispatch(payload: dict, *, require_action_fn, interpret_document_fn, healthcheck_fn, debug_run_fn, generate_llm_fn=None) -> dict:
    try:
        action = require_action_fn(payload)
    except ValueError as exc:
        return error_response(str(exc))
    if action == INTERPRET_DOCUMENT_ACTION:
        return interpret_document_fn(payload)
    if action == HEALTHCHECK_ACTION:
        return healthcheck_fn(payload)
    if action == DEBUG_RUN_ACTION:
        return debug_run_fn(payload)
    if action == GENERATE_LLM_ACTION and generate_llm_fn is not None:
        return generate_llm_fn(payload)
    return error_response(f"Unbekannte Aktion: {action}")


def _dependency_error(*, detail: str) -> dict:
    return {
        "status": "error",
        "healthy": False,
        "message": "Interpreter-Provider nicht bereit.",
        "dependencies": [_dependency_payload(healthy=False, detail=detail)],
    }


def _dependency_payload(*, healthy: bool, detail: str) -> dict[str, Any]:
    return {
        "name": "llm_provider",
        "kind": "service",
        "required": True,
        "healthy": healthy,
        "detail": detail,
    }


def _build_effective_config(config, runtime_settings) -> Any:
    config.model = runtime_settings.model
    config.max_output_tokens = runtime_settings.max_output_tokens
    config.thinking_effort = "no thinking"
    return config


def _healthcheck_messages() -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "Return valid json only. Return the requested payload exactly. No prose."},
        {"role": "user", "content": 'Return exactly this json object: {"accepted":true}'},
    ]


def _runtime_detail(config) -> str:
    return (
        f"{config.api_base_url} "
        f"({config.model}, max_output_tokens={config.max_output_tokens}, reasoning={config.api_thinking_effort})"
    )


def _run_debug_action(payload: dict, action, *, summary: str) -> dict:
    try:
        return action()
    except Exception as exc:
        return _debug_error(payload, summary=summary, message=str(exc))


def _debug_error(payload: dict, *, summary: str, message: str) -> dict:
    session_root_text = str(payload.get("session_root", "")).strip()
    if not session_root_text:
        return error_response(message)
    session_root = Path(session_root_text)
    if debug_support.cancel_requested(session_root):
        debug_support.write_snapshot(session_root, status="cancelled", detail=summary)
        return debug_support.write_result(session_root, {"status": "cancelled", "summary": summary})
    debug_support.append_log(session_root, f"[ERROR] {message}")
    debug_support.write_snapshot(session_root, status="error", detail=message)
    return debug_support.write_result(session_root, {"status": "error", "summary": summary, "error": message})
