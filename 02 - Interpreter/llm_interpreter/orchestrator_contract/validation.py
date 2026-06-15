"""Hard contract validation for the vision interpreter subprocess surface."""
from __future__ import annotations

from pathlib import Path

from .types import (
    DEBUG_RUN_ACTION,
    GENERATE_LLM_ACTION,
    HEALTHCHECK_ACTION,
    INTERPRET_DOCUMENT_ACTION,
    ActionName,
    DebugRunCommand,
    GenerateLLMCommand,
    HealthcheckCommand,
    InterpreterRuntimeSettings,
    InterpretDocumentCommand,
)


def normalize_action(payload: dict) -> str:
    return str(payload.get("action", "")).strip()


def require_action(payload: dict) -> ActionName:
    action = normalize_action(payload)
    if action == INTERPRET_DOCUMENT_ACTION:
        return INTERPRET_DOCUMENT_ACTION
    if action == HEALTHCHECK_ACTION:
        return HEALTHCHECK_ACTION
    if action == DEBUG_RUN_ACTION:
        return DEBUG_RUN_ACTION
    if action == GENERATE_LLM_ACTION:
        return GENERATE_LLM_ACTION
    raise ValueError(f"Unbekannte Aktion: {action}")


def parse_interpret_document_command(payload: dict) -> InterpretDocumentCommand:
    request_path_text = _required_path_text(payload, "request_path", "request_path fehlt.")
    output_path_text = _required_path_text(payload, "structured_output_path", "structured_output_path fehlt.")
    command = InterpretDocumentCommand(
        request_path=Path(request_path_text),
        structured_output_path=Path(output_path_text),
        debug_bundle_dir=_optional_path(payload, "debug_bundle_dir"),
        runtime_settings=parse_runtime_settings(payload),
    )
    if not command.request_path.exists() or not command.request_path.is_file():
        raise ValueError(f"Request nicht gefunden: {command.request_path}")
    return command


def parse_healthcheck_command(payload: dict) -> HealthcheckCommand:
    return HealthcheckCommand(runtime_settings=parse_runtime_settings(payload))


def parse_debug_run_command(payload: dict) -> DebugRunCommand:
    output_root_text = _required_path_text(payload, "output_root", "output_root fehlt.")
    session_root_text = _required_path_text(payload, "session_root", "session_root fehlt.")
    mode = _parse_debug_mode(payload)
    request_path = None
    input_root = None
    if mode == "single":
        request_path = Path(_required_path_text(payload, "request_path", "request_path fehlt."))
        if not request_path.exists() or not request_path.is_file():
            raise ValueError(f"Request nicht gefunden: {request_path}")
    else:
        input_root = Path(_required_path_text(payload, "input_root", "input_root fehlt."))
        if not input_root.exists():
            raise ValueError(f"Batch-Input nicht gefunden: {input_root}")
    command = DebugRunCommand(
        session_root=Path(session_root_text),
        mode=mode,
        request_path=request_path,
        input_root=input_root,
        output_root=Path(output_root_text),
        num_workers=_parse_num_workers(payload),
        runtime_settings=parse_runtime_settings(payload),
    )
    return command


def parse_generate_llm_command(payload: dict) -> GenerateLLMCommand:
    runtime_settings = parse_runtime_settings(payload)
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages fehlt oder ist ungueltig.")
    parsed_messages: list[dict] = []
    for item in messages:
        if not isinstance(item, dict):
            raise ValueError("messages muss JSON-Objekte enthalten.")
        role = str(item.get("role", "")).strip()
        if role not in {"system", "user", "assistant"}:
            raise ValueError("messages.role ist ungueltig.")
        if "content" not in item:
            raise ValueError("messages.content fehlt.")
        parsed_messages.append(dict(item))
    target_schema = payload.get("target_schema")
    if target_schema is not None and not isinstance(target_schema, dict):
        raise ValueError("target_schema muss ein JSON-Objekt sein.")
    return GenerateLLMCommand(
        runtime_settings=runtime_settings,
        messages=tuple(parsed_messages),
        target_schema=dict(target_schema) if isinstance(target_schema, dict) else None,
        max_output_tokens=_optional_positive_int(
            payload.get("max_output_tokens"),
            default=runtime_settings.max_output_tokens,
            field="max_output_tokens",
        ),
    )


def parse_runtime_settings(payload: dict) -> InterpreterRuntimeSettings:
    settings = payload.get("runtime_settings")
    if not isinstance(settings, dict):
        raise ValueError("runtime_settings fehlt.")
    model = str(settings.get("model", "")).strip()
    if not model:
        raise ValueError("runtime_settings.model fehlt.")
    max_output_tokens = settings.get("max_output_tokens")
    if isinstance(max_output_tokens, bool):
        raise ValueError("runtime_settings.max_output_tokens muss eine positive Ganzzahl sein.")
    try:
        parsed_max_output_tokens = int(max_output_tokens)
    except (TypeError, ValueError):
        raise ValueError("runtime_settings.max_output_tokens muss eine positive Ganzzahl sein.") from None
    if parsed_max_output_tokens < 1:
        raise ValueError("runtime_settings.max_output_tokens muss eine positive Ganzzahl sein.")
    return InterpreterRuntimeSettings(model=model, max_output_tokens=parsed_max_output_tokens)


def _required_path_text(payload: dict, key: str, message: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(message)
    return value


def _optional_path(payload: dict, key: str) -> Path | None:
    value = str(payload.get(key, "")).strip()
    return Path(value) if value else None


def _parse_debug_mode(payload: dict) -> str:
    mode = str(payload.get("mode", "single")).strip().lower() or "single"
    if mode not in {"single", "batch"}:
        raise ValueError("mode muss 'single' oder 'batch' sein.")
    return mode


def _parse_num_workers(payload: dict) -> int:
    value = payload.get("num_workers", 1)
    if isinstance(value, bool):
        raise ValueError("num_workers muss eine positive Ganzzahl sein.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("num_workers muss eine positive Ganzzahl sein.") from None
    if parsed < 1:
        raise ValueError("num_workers muss eine positive Ganzzahl sein.")
    return parsed


def _optional_positive_int(value, *, default: int, field: str) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        raise ValueError(f"{field} muss eine positive Ganzzahl sein.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} muss eine positive Ganzzahl sein.") from None
    if parsed < 1:
        raise ValueError(f"{field} muss eine positive Ganzzahl sein.")
    return parsed
