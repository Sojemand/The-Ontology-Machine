from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .tool_handler_deps import ToolFailure, _invoke_edit, _invoke_product, _positive_int, _required_mapping, _required_text

_INTERPRET_ARGS = {"request_root", "request_path", "output_root", "structured_output_path", "runtime_settings", "debug_bundle_dir", "timeout_seconds"}
_HEALTHCHECK_ARGS = {"runtime_settings", "timeout_seconds"}
_RUNTIME_SETTING_KEYS = {"model", "max_output_tokens"}
_MAX_OUTPUT_TOKENS = 200_000
_MAX_TIMEOUT_SECONDS = 3600
_SECRET_FIELD_RE = re.compile(r"(api[_-]?key|authorization|credential|password|secret|access[_-]?token|refresh[_-]?token|oauth.*token)", re.IGNORECASE)
_PROVIDER_TOKEN_RE = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|ya29\.[A-Za-z0-9_-]{12,})\b")


def interpreter_interpret_document(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _INTERPRET_ARGS, "interpreter.interpret_document")
    request_root = _existing_dir(arguments, "request_root")
    output_root = _existing_dir(arguments, "output_root")
    request_path = _existing_file(arguments, "request_path", root=request_root)
    structured_output_path = _output_path(arguments, "structured_output_path", root=output_root)
    payload: dict[str, Any] = {
        "action": "interpret_document",
        "request_path": str(request_path),
        "structured_output_path": str(structured_output_path),
        "runtime_settings": _runtime_settings(arguments),
    }
    debug_bundle_dir = _optional_output_dir(arguments, "debug_bundle_dir", root=output_root)
    if debug_bundle_dir is not None:
        payload["debug_bundle_dir"] = str(debug_bundle_dir)
    return _invoke_interpreter(payload, arguments)


def interpreter_healthcheck(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _HEALTHCHECK_ARGS, "interpreter.healthcheck")
    return _invoke_interpreter({"action": "healthcheck", "runtime_settings": _runtime_settings(arguments)}, arguments)


def interpreter_describe_surfaces(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, set(), "interpreter.describe_surfaces")
    return _safe_result(_invoke_edit("interpreter", {"action": "describe_surfaces"}))


def interpreter_read_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id"}, "interpreter.read_surface")
    return _safe_result(_invoke_edit("interpreter", {"action": "read_surface", "surface_id": _required_text(arguments, "surface_id")}))


def interpreter_validate_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id", "value"}, "interpreter.validate_surface")
    value = _required_mapping(arguments, "value")
    _ensure_no_secret_material(value, path="value")
    payload = {"action": "validate_surface", "surface_id": _required_text(arguments, "surface_id"), "value": value}
    return _safe_result(_invoke_edit("interpreter", payload))


def interpreter_write_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id", "value"}, "interpreter.write_surface")
    value = _required_mapping(arguments, "value")
    _ensure_no_secret_material(value, path="value")
    payload = {"action": "write_surface", "surface_id": _required_text(arguments, "surface_id"), "value": value}
    return _safe_result(_invoke_edit("interpreter", payload))


def _invoke_interpreter(payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    timeout = _timeout_seconds(arguments)
    if timeout is None:
        return _invoke_product("interpreter", payload)
    return _invoke_product("interpreter", payload, timeout=timeout)


def _runtime_settings(arguments: dict[str, Any]) -> dict[str, Any]:
    settings = _required_mapping(arguments, "runtime_settings")
    unknown = sorted(set(settings) - _RUNTIME_SETTING_KEYS)
    if unknown:
        raise ToolFailure(f"runtime_settings kennt diese Felder nicht: {', '.join(unknown)}")
    model = str(settings.get("model") or "").strip()
    if not model:
        raise ToolFailure("runtime_settings.model fehlt oder ist ungueltig.")
    max_output_tokens = _positive_int(settings.get("max_output_tokens"), "runtime_settings.max_output_tokens")
    if max_output_tokens > _MAX_OUTPUT_TOKENS:
        raise ToolFailure(f"runtime_settings.max_output_tokens darf hoechstens {_MAX_OUTPUT_TOKENS} sein.")
    return {"model": model, "max_output_tokens": max_output_tokens}


def _reject_unknown(arguments: dict[str, Any], allowed: set[str], tool_name: str) -> None:
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ToolFailure(f"{tool_name} kennt diese Argumente nicht: {', '.join(unknown)}")


def _safe_result(result: dict[str, Any]) -> dict[str, Any]:
    _ensure_no_secret_material(result, path="result")
    return result


def _ensure_no_secret_material(value: Any, *, path: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            text_key = str(key)
            child_path = f"{path}.{text_key}"
            if _SECRET_FIELD_RE.search(text_key):
                raise ToolFailure(f"Interpreter-Surface enthaelt ein Credential-Feld: {child_path}")
            _ensure_no_secret_material(item, path=child_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _ensure_no_secret_material(item, path=f"{path}[{index}]")
    elif isinstance(value, str) and _PROVIDER_TOKEN_RE.search(value):
        raise ToolFailure(f"Interpreter-Surface enthaelt Provider-Token-Material: {path}")


def _existing_dir(arguments: dict[str, Any], key: str) -> Path:
    path = Path(_required_text(arguments, key)).expanduser().resolve()
    if not path.exists():
        raise ToolFailure(f"{key} existiert nicht: {path}")
    if not path.is_dir():
        raise ToolFailure(f"{key} muss ein Ordner sein: {path}")
    return path


def _existing_file(arguments: dict[str, Any], key: str, *, root: Path) -> Path:
    path = _resolve_candidate(_required_text(arguments, key), root=root)
    if not _is_within(path, root):
        raise ToolFailure(f"{key} muss innerhalb von request_root liegen.")
    if not path.exists():
        raise ToolFailure(f"{key} existiert nicht: {path}")
    if not path.is_file():
        raise ToolFailure(f"{key} muss eine Datei sein: {path}")
    return path


def _output_path(arguments: dict[str, Any], key: str, *, root: Path) -> Path:
    path = _resolve_candidate(_required_text(arguments, key), root=root)
    if not _is_within(path, root):
        raise ToolFailure(f"{key} muss innerhalb von output_root liegen.")
    if path.exists() and not path.is_file():
        raise ToolFailure(f"{key} muss eine Datei sein: {path}")
    return path


def _optional_output_dir(arguments: dict[str, Any], key: str, *, root: Path) -> Path | None:
    value = arguments.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ToolFailure(f"{key} muss ein String sein.")
    path = _resolve_candidate(value.strip(), root=root)
    if not _is_within(path, root):
        raise ToolFailure(f"{key} muss innerhalb von output_root liegen.")
    if path.exists() and not path.is_dir():
        raise ToolFailure(f"{key} muss ein Ordner sein: {path}")
    return path


def _resolve_candidate(value: str, *, root: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _timeout_seconds(arguments: dict[str, Any]) -> int | None:
    if "timeout_seconds" not in arguments or arguments.get("timeout_seconds") in (None, ""):
        return None
    timeout = _positive_int(arguments["timeout_seconds"], "timeout_seconds")
    if timeout > _MAX_TIMEOUT_SECONDS:
        raise ToolFailure(f"timeout_seconds darf hoechstens {_MAX_TIMEOUT_SECONDS} sein.")
    return timeout


__all__ = [name for name in globals() if not name.startswith("__")]
