from __future__ import annotations

from pathlib import Path
from typing import Any

from .tool_handler_deps import ToolFailure, _invoke_product, _positive_int, _required_text

_VALIDATE_ARGS = {
    "structured_root",
    "structured_path",
    "validation_root",
    "validation_output_path",
    "raw_root",
    "raw_path",
    "timeout_seconds",
}
_HEALTHCHECK_ARGS = {"timeout_seconds"}
_MAX_TIMEOUT_SECONDS = 3600


def validator_validate_document(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _VALIDATE_ARGS, "validator.validate_document")
    structured_root = _existing_dir(arguments, "structured_root")
    validation_root = _existing_dir(arguments, "validation_root")
    structured_path = _existing_file(arguments, "structured_path", root=structured_root, root_name="structured_root")
    validation_output_path = _output_path(arguments, "validation_output_path", root=validation_root)
    payload: dict[str, Any] = {
        "action": "validate_document",
        "structured_path": str(structured_path),
        "validation_output_path": str(validation_output_path),
    }
    raw_path = _optional_raw_path(arguments)
    if raw_path is not None:
        payload["raw_path"] = str(raw_path)
    return _invoke_validator(payload, arguments)


def validator_healthcheck(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _HEALTHCHECK_ARGS, "validator.healthcheck")
    return _invoke_validator({"action": "healthcheck"}, arguments)


def _optional_raw_path(arguments: dict[str, Any]) -> Path | None:
    raw_value = arguments.get("raw_path")
    raw_root_value = arguments.get("raw_root")
    if raw_value in (None, ""):
        if raw_root_value not in (None, ""):
            raise ToolFailure("raw_root ist nur zusammen mit raw_path erlaubt.")
        return None
    if raw_root_value in (None, ""):
        raise ToolFailure("raw_root fehlt oder ist ungueltig.")
    raw_root = _existing_dir(arguments, "raw_root")
    return _existing_file(arguments, "raw_path", root=raw_root, root_name="raw_root")


def _invoke_validator(payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    timeout = _timeout_seconds(arguments)
    if timeout is None:
        return _invoke_product("validator", payload)
    return _invoke_product("validator", payload, timeout=timeout)


def _reject_unknown(arguments: dict[str, Any], allowed: set[str], tool_name: str) -> None:
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ToolFailure(f"{tool_name} kennt diese Argumente nicht: {', '.join(unknown)}")


def _existing_dir(arguments: dict[str, Any], key: str) -> Path:
    path = Path(_required_text(arguments, key)).expanduser().resolve()
    if not path.exists():
        raise ToolFailure(f"{key} existiert nicht: {path}")
    if not path.is_dir():
        raise ToolFailure(f"{key} muss ein Ordner sein: {path}")
    return path


def _existing_file(arguments: dict[str, Any], key: str, *, root: Path, root_name: str) -> Path:
    path = _resolve_candidate(_required_text(arguments, key), root=root)
    if not _is_within(path, root):
        raise ToolFailure(f"{key} muss innerhalb von {root_name} liegen.")
    if not path.exists():
        raise ToolFailure(f"{key} existiert nicht: {path}")
    if not path.is_file():
        raise ToolFailure(f"{key} muss eine Datei sein: {path}")
    return path


def _output_path(arguments: dict[str, Any], key: str, *, root: Path) -> Path:
    path = _resolve_candidate(_required_text(arguments, key), root=root)
    if not _is_within(path, root):
        raise ToolFailure(f"{key} muss innerhalb von validation_root liegen.")
    if path.exists() and not path.is_file():
        raise ToolFailure(f"{key} muss eine Datei sein: {path}")
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
