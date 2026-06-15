from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .tool_handler_deps import *

_OPTIMIZER_PROFILES = {"vision", "file"}
_HEALTHCHECK_DEPENDENCIES = {
    "pdf-pdfplumber",
    "ocr-paddleocr-gpu",
    "ocr-paddleocr-cpu",
    "ocr-paddleocr",
    "pdf-pymupdf",
    "docx-python",
    "odt-odfpy",
    "rtf-reader",
    "mail-rfc822",
    "mail-outlook-msg",
    "mail-outlook-store",
    "renderer-pdf",
    "renderer-office",
    "renderer-html",
}
_FILTER_KEYS = {"format", "doc_type", "max_size_mb", "batch_size"}
_HASH_TOOL_KEYS = {"use_processed_hashes"}


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


def _existing_file(arguments: dict[str, Any], key: str, *, root: Path | None = None) -> Path:
    path = _resolve_candidate(_required_text(arguments, key), root=root)
    if root is not None and not _is_within(path, root):
        raise ToolFailure(f"{key} muss innerhalb von input_root liegen.")
    if not path.exists():
        raise ToolFailure(f"{key} existiert nicht: {path}")
    if not path.is_file():
        raise ToolFailure(f"{key} muss eine Datei sein: {path}")
    return path


def _output_path(arguments: dict[str, Any], key: str, *, root: Path) -> Path:
    path = _resolve_candidate(_required_text(arguments, key), root=root)
    if not _is_within(path, root):
        raise ToolFailure(f"{key} muss innerhalb von output_root liegen.")
    return path


def _session_root(arguments: dict[str, Any], debug_root: Path) -> Path:
    path = _resolve_candidate(_required_text(arguments, "session_root"), root=debug_root)
    if not _is_within(path, debug_root):
        raise ToolFailure("session_root muss innerhalb von debug_root liegen.")
    return path


def _resolve_candidate(value: str, *, root: Path | None) -> Path:
    path = Path(value).expanduser()
    if root is not None and not path.is_absolute():
        path = root / path
    return path.resolve()


def _optimizer_profile(arguments: dict[str, Any], *, required: bool) -> str:
    if "optimizer_profile" not in arguments or arguments.get("optimizer_profile") in (None, ""):
        if required:
            raise ToolFailure("optimizer_profile fehlt oder ist ungueltig.")
        return ""
    profile = _required_text(arguments, "optimizer_profile").casefold()
    if profile not in _OPTIMIZER_PROFILES:
        raise ToolFailure("optimizer_profile muss 'vision' oder 'file' sein.")
    return profile


def _runtime_policy_path(arguments: dict[str, Any], *, required: bool) -> Path | None:
    raw = _optional_text(arguments, "runtime_policy_path")
    if not raw:
        if required:
            raise ToolFailure("runtime_policy_path ist fuer optimizer_profile=vision erforderlich.")
        return None
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise ToolFailure(f"runtime_policy_path existiert nicht: {path}")
    if not path.is_file():
        raise ToolFailure(f"runtime_policy_path muss eine Datei sein: {path}")
    return path


def _relative_logical_path(arguments: dict[str, Any]) -> str:
    raw = _required_text(arguments, "logical_source_path")
    windows_path = PureWindowsPath(raw)
    posix_text = raw.replace("\\", "/")
    posix_path = PurePosixPath(posix_text)
    if windows_path.is_absolute() or windows_path.drive or windows_path.root or posix_path.is_absolute():
        raise ToolFailure("logical_source_path muss relativ sein.")
    parts: list[str] = []
    for part in posix_text.split("/"):
        normalized = part.strip()
        if not normalized or normalized == ".":
            continue
        if normalized == ".." or ":" in normalized:
            raise ToolFailure("logical_source_path muss innerhalb der Pipeline bleiben.")
        parts.append(normalized)
    if not parts:
        raise ToolFailure("logical_source_path fehlt oder ist ungueltig.")
    return "/".join(parts)


def _healthcheck_dependencies(arguments: dict[str, Any]) -> list[str]:
    value = arguments.get("required_dependencies")
    if value is None:
        return []
    if not isinstance(value, list):
        raise ToolFailure("required_dependencies muss eine String-Liste sein.")
    dependencies: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ToolFailure("required_dependencies muss eine String-Liste sein.")
        name = item.strip()
        if not name:
            raise ToolFailure("required_dependencies enthaelt einen leeren Eintrag.")
        if name not in _HEALTHCHECK_DEPENDENCIES:
            raise ToolFailure(f"required_dependencies enthaelt unbekannte Abhaengigkeit: {name}")
        if name not in dependencies:
            dependencies.append(name)
    return dependencies


def _filters(arguments: dict[str, Any]) -> dict[str, Any]:
    value = arguments.get("filters")
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ToolFailure("filters muss ein Objekt sein.")
    unknown = sorted(set(value) - _FILTER_KEYS)
    if unknown:
        raise ToolFailure(f"filters kennt diese Felder nicht: {', '.join(unknown)}")
    return {**_text_filters(value), **_int_filters(value)}


def _text_filters(value: dict[str, Any]) -> dict[str, str]:
    filters: dict[str, str] = {}
    for key in ("format", "doc_type"):
        raw = value.get(key)
        if raw is None:
            continue
        if not isinstance(raw, str):
            raise ToolFailure(f"filters.{key} muss ein String sein.")
        text = raw.strip()
        if text:
            filters[key] = text
    return filters


def _int_filters(value: dict[str, Any]) -> dict[str, int]:
    filters: dict[str, int] = {}
    for key in ("max_size_mb", "batch_size"):
        if key in value and value[key] is not None:
            filters[key] = _positive_or_zero_int(value[key], f"filters.{key}")
    return filters


def _hash_tools(arguments: dict[str, Any]) -> dict[str, Any]:
    value = arguments.get("hash_tools")
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ToolFailure("hash_tools muss ein Objekt sein.")
    unknown = sorted(set(value) - _HASH_TOOL_KEYS)
    if unknown:
        raise ToolFailure(f"hash_tools kennt diese Felder nicht: {', '.join(unknown)}")
    if "use_processed_hashes" not in value:
        return {}
    if not isinstance(value["use_processed_hashes"], bool):
        raise ToolFailure("hash_tools.use_processed_hashes muss ein Bool sein.")
    return {"use_processed_hashes": value["use_processed_hashes"]}


def _timeout_seconds(arguments: dict[str, Any]) -> int | None:
    if "timeout_seconds" not in arguments or arguments.get("timeout_seconds") in (None, ""):
        return None
    return _positive_int(arguments["timeout_seconds"], "timeout_seconds")


__all__ = [name for name in globals() if not name.startswith("__")]
