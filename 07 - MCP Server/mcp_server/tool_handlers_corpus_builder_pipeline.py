from __future__ import annotations

from pathlib import Path
from typing import Any

from .tool_handler_deps import *

_CORPUS_LOAD_KEYS = {
    "artifact_root",
    "normalized_path",
    "structured_path",
    "validation_path",
    "raw_path",
    "corpus_db_path",
    "corpus_output_folder",
    "persist_page_images_in_db",
    "page_images_dir",
    "timeout_seconds",
}
_CORPUS_HEALTHCHECK_KEYS = {"runtime_model", "scope", "timeout_seconds"}
_CORPUS_SCAN_KEYS = {"input_root", "debug_root", "session_root", "timeout_seconds"}


def corpus_builder_load_document(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _CORPUS_LOAD_KEYS, "corpus_builder.load_document")
    artifact_root = _existing_dir(arguments, "artifact_root")
    corpus_output_folder = _existing_dir(arguments, "corpus_output_folder")
    normalized_path = _existing_file(arguments, "normalized_path", root=artifact_root)
    structured_path = _existing_file(arguments, "structured_path", root=artifact_root)
    validation_path = _existing_file(arguments, "validation_path", root=artifact_root)
    corpus_db_path = _existing_file(arguments, "corpus_db_path", root=corpus_output_folder)
    _validate_storage_contains_db(corpus_db_path, corpus_output_folder)
    payload = _load_payload(arguments, artifact_root, corpus_db_path, normalized_path, structured_path, validation_path)
    return _invoke_corpus_builder(payload, arguments)


def corpus_builder_healthcheck(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _CORPUS_HEALTHCHECK_KEYS, "corpus_builder.healthcheck")
    payload: dict[str, Any] = {
        "action": "healthcheck",
        "runtime_settings": {"model": _required_text(arguments, "runtime_model")},
    }
    scope = _optional_text(arguments, "scope")
    if scope:
        payload["scope"] = scope
    return _invoke_corpus_builder(payload, arguments)


def corpus_builder_scan_debug_input(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _CORPUS_SCAN_KEYS, "corpus_builder.scan_debug_input")
    input_root = _existing_dir(arguments, "input_root")
    debug_root = _existing_dir(arguments, "debug_root")
    payload = {
        "action": "scan_debug_input",
        "input_root": str(input_root),
        "session_root": str(_session_root(arguments, debug_root)),
        "mode": "scan",
    }
    return _invoke_corpus_builder(payload, arguments)


def _load_payload(
    arguments: dict[str, Any],
    artifact_root: Path,
    corpus_db_path: Path,
    normalized_path: Path,
    structured_path: Path,
    validation_path: Path,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "action": "load_document",
        "corpus_db_path": str(corpus_db_path),
        "normalized_path": str(normalized_path),
        "structured_path": str(structured_path),
        "validation_path": str(validation_path),
    }
    raw_path = _optional_existing_file(arguments, "raw_path", root=artifact_root)
    if raw_path is not None:
        payload["raw_path"] = str(raw_path)
    if "persist_page_images_in_db" in arguments:
        payload["persist_page_images_in_db"] = _optional_bool(arguments, "persist_page_images_in_db", default=True)
    page_images_dir = _optional_existing_dir(arguments, "page_images_dir", root=artifact_root)
    if page_images_dir is not None:
        payload["page_images_dir"] = str(page_images_dir)
    return payload


def _invoke_corpus_builder(payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    timeout = _timeout_seconds(arguments)
    if timeout is None:
        return _invoke_product("corpus_builder", payload)
    return _invoke_product("corpus_builder", payload, timeout=timeout)


def _reject_unknown(arguments: dict[str, Any], allowed: set[str], tool_name: str) -> None:
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ToolFailure(f"{tool_name} kennt diese Argumente nicht: {', '.join(unknown)}")


def _existing_dir(arguments: dict[str, Any], key: str, *, root: Path | None = None) -> Path:
    path = _resolve_candidate(_required_text(arguments, key), root=root)
    if root is not None and not _is_within(path, root):
        raise ToolFailure(f"{key} muss innerhalb von {root.name or 'root'} liegen.")
    if not path.exists():
        raise ToolFailure(f"{key} existiert nicht: {path}")
    if not path.is_dir():
        raise ToolFailure(f"{key} muss ein Ordner sein: {path}")
    return path


def _optional_existing_dir(arguments: dict[str, Any], key: str, *, root: Path) -> Path | None:
    raw = _optional_text(arguments, key)
    if not raw:
        return None
    path = _resolve_candidate(raw, root=root)
    _validate_optional_path(path, root, key, "artifact_root")
    if not path.is_dir():
        raise ToolFailure(f"{key} muss ein Ordner sein: {path}")
    return path


def _existing_file(arguments: dict[str, Any], key: str, *, root: Path) -> Path:
    path = _resolve_candidate(_required_text(arguments, key), root=root)
    root_key = "corpus_output_folder" if key == "corpus_db_path" else "artifact_root"
    _validate_optional_path(path, root, key, root_key)
    if not path.is_file():
        raise ToolFailure(f"{key} muss eine Datei sein: {path}")
    return path


def _optional_existing_file(arguments: dict[str, Any], key: str, *, root: Path) -> Path | None:
    raw = _optional_text(arguments, key)
    if not raw:
        return None
    path = _resolve_candidate(raw, root=root)
    _validate_optional_path(path, root, key, "artifact_root")
    if not path.is_file():
        raise ToolFailure(f"{key} muss eine Datei sein: {path}")
    return path


def _validate_optional_path(path: Path, root: Path, key: str, root_key: str) -> None:
    if not _is_within(path, root):
        raise ToolFailure(f"{key} muss innerhalb von {root_key} liegen.")
    if not path.exists():
        raise ToolFailure(f"{key} existiert nicht: {path}")


def _session_root(arguments: dict[str, Any], debug_root: Path) -> Path:
    path = _resolve_candidate(_required_text(arguments, "session_root"), root=debug_root)
    if not _is_within(path, debug_root):
        raise ToolFailure("session_root muss innerhalb von debug_root liegen.")
    if path.exists() and not path.is_dir():
        raise ToolFailure(f"session_root muss ein Ordner sein: {path}")
    return path


def _resolve_candidate(value: str, *, root: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if root is not None and not path.is_absolute():
        path = root / path
    return path.resolve()


def _timeout_seconds(arguments: dict[str, Any]) -> int | None:
    if "timeout_seconds" not in arguments or arguments.get("timeout_seconds") in (None, ""):
        return None
    return _positive_int(arguments["timeout_seconds"], "timeout_seconds")


__all__ = [name for name in globals() if not name.startswith("__")]
