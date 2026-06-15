"""Hard contract validation for the validator subprocess surface."""

from __future__ import annotations

from pathlib import Path

from .types import (
    DEBUG_RUN_ACTION,
    HEALTHCHECK_ACTION,
    VALIDATE_DOCUMENT_ACTION,
    ActionName,
    DebugRunCommand,
    ValidateDocumentCommand,
)

_DEBUG_RUN_MODES = ("single", "batch")
_LEGACY_VALIDATE_DOCUMENT_FIELDS = ("output_dir", "raw_root", "report_name")
_CHECK_KEYS = ("free_text", "context_scalars", "content_fields", "rows")


def require_action(payload: dict) -> ActionName:
    action = _required_string(payload, "action")
    if action is None:
        raise ValueError("action fehlt oder ist ungueltig.")
    if action in {VALIDATE_DOCUMENT_ACTION, HEALTHCHECK_ACTION, DEBUG_RUN_ACTION}:
        return action
    raise ValueError(f"Unbekannte Aktion: {action}")


def parse_validate_document_command(payload: dict) -> ValidateDocumentCommand:
    _reject_legacy_validate_document_fields(payload)
    structured_value = _required_string(payload, "structured_path")
    if structured_value is None:
        raise ValueError("structured_path fehlt oder ist ungueltig.")
    output_value = _required_string(payload, "validation_output_path")
    if output_value is None:
        raise ValueError("validation_output_path fehlt oder ist ungueltig.")
    raw_value = _optional_string(payload, "raw_path")
    command = ValidateDocumentCommand(
        structured_path=Path(structured_value),
        validation_output_path=Path(output_value),
        raw_path=Path(raw_value) if raw_value is not None else None,
    )
    if not command.structured_path.exists():
        raise ValueError(f"Structured JSON nicht gefunden: {command.structured_path}")
    if not command.structured_path.is_file():
        raise ValueError(f"Structured JSON muss eine Datei sein: {command.structured_path}")
    if command.validation_output_path.exists() and not command.validation_output_path.is_file():
        raise ValueError(f"validation_output_path muss eine Datei sein: {command.validation_output_path}")
    if command.raw_path is not None:
        if not command.raw_path.exists():
            raise ValueError(f"Raw JSON nicht gefunden: {command.raw_path}")
        if not command.raw_path.is_file():
            raise ValueError(f"Raw JSON muss eine Datei sein: {command.raw_path}")
    return command


def parse_debug_run_command(payload: dict) -> DebugRunCommand:
    mode = _required_string(payload, "mode")
    if mode not in _DEBUG_RUN_MODES:
        raise ValueError(f"mode muss {' oder '.join(_DEBUG_RUN_MODES)} sein.")
    session_root = _required_path(payload, "session_root")
    output_root = _required_path(payload, "output_root")
    _require_path_inside(output_root, session_root, child_name="output_root", parent_name="session_root")
    options = _optional_object(payload.get("options"), field_name="options")
    raw_evidence = _optional_object(options.get("raw_evidence"), field_name="options.raw_evidence")
    check_toggles = _parse_check_toggles(options.get("check_toggles"))
    if mode == "single":
        source_path = _required_path(payload, "source_path")
        if not source_path.exists():
            raise ValueError(f"Structured JSON nicht gefunden: {source_path}")
        if not source_path.is_file():
            raise ValueError(f"Structured JSON muss eine Datei sein: {source_path}")
        input_root = _optional_path(payload.get("input_root")) or source_path.parent
        if not input_root.exists():
            raise ValueError(f"Structured-Ordner nicht gefunden: {input_root}")
        if not input_root.is_dir():
            raise ValueError(f"Structured-Eingabe muss ein Ordner sein: {input_root}")
    else:
        source_path = None
        input_root = _required_path(payload, "input_root")
        if not input_root.exists():
            raise ValueError(f"Structured-Ordner nicht gefunden: {input_root}")
        if not input_root.is_dir():
            raise ValueError(f"Structured-Eingabe muss ein Ordner sein: {input_root}")
    raw_path = _optional_path(raw_evidence.get("raw_path"))
    raw_root = _optional_path(raw_evidence.get("raw_root"))
    if raw_path is not None:
        if not raw_path.exists():
            raise ValueError(f"Raw JSON nicht gefunden: {raw_path}")
        if not raw_path.is_file():
            raise ValueError(f"Raw JSON muss eine Datei sein: {raw_path}")
    if raw_root is not None:
        if not raw_root.exists():
            raise ValueError(f"Raw-Ordner nicht gefunden: {raw_root}")
        if not raw_root.is_dir():
            raise ValueError(f"Raw-Ordner muss ein Verzeichnis sein: {raw_root}")
    return DebugRunCommand(
        mode=mode,
        session_root=session_root,
        output_root=output_root,
        source_path=source_path,
        input_root=input_root,
        raw_path=raw_path,
        raw_root=raw_root,
        check_toggles=check_toggles,
    )


def _reject_legacy_validate_document_fields(payload: dict) -> None:
    for field in _LEGACY_VALIDATE_DOCUMENT_FIELDS:
        if field in payload:
            raise ValueError(f"Legacy-Feld nicht erlaubt: {field}")


def _required_path(payload: dict, key: str) -> Path:
    value = _required_string(payload, key)
    if value is None:
        raise ValueError(f"{key} fehlt oder ist ungueltig.")
    return Path(value)


def _optional_path(value: object) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Pfadoptionen muessen Strings sein.")
    stripped = value.strip()
    return Path(stripped) if stripped else None


def _optional_object(value: object, *, field_name: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} muss ein Objekt sein.")
    return value


def _parse_check_toggles(value: object) -> dict[str, bool]:
    toggles = _optional_object(value, field_name="options.check_toggles")
    unknown = sorted(key for key in toggles if key not in _CHECK_KEYS)
    if unknown:
        raise ValueError(f"Unbekannte Check-Toggles: {', '.join(unknown)}")
    parsed: dict[str, bool] = {}
    for key in _CHECK_KEYS:
        item = toggles.get(key, True)
        if not isinstance(item, bool):
            raise ValueError(f"options.check_toggles.{key} muss true oder false sein.")
        parsed[key] = item
    return parsed


def _required_string(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_string(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} fehlt oder ist ungueltig.")
    stripped = value.strip()
    return stripped or None


def _require_path_inside(child: Path, parent: Path, *, child_name: str, parent_name: str) -> None:
    child_resolved = child.expanduser().resolve(strict=False)
    parent_resolved = parent.expanduser().resolve(strict=False)
    if not child_resolved.is_relative_to(parent_resolved):
        raise ValueError(f"{child_name} muss innerhalb von {parent_name} liegen.")
