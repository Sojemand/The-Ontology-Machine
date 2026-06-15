"""Path boundary checks for orchestrator contract payloads."""
from __future__ import annotations

from pathlib import Path

from .types import DebugRunCommand

STRUCTURED_JSON_SUFFIX = ".structured.json"
JSON_SUFFIX = ".json"
FORBIDDEN_DEBUG_ROOT_NAMES = frozenset({"config", "runtime", "vendor"})


def require_structured_json_path(path, *, label: str) -> None:
    if not str(path.name).lower().endswith(STRUCTURED_JSON_SUFFIX):
        raise ValueError(f"{label} muss auf *{STRUCTURED_JSON_SUFFIX} enden: {path}")


def require_json_file_path(path, *, label: str) -> None:
    if path.suffix.lower() != JSON_SUFFIX:
        raise ValueError(f"{label} muss eine JSON-Datei sein: {path}")


def validate_output_json_path(path, *, label: str) -> None:
    if path.exists() and path.is_dir():
        raise ValueError(f"{label} darf kein Verzeichnis sein: {path}")
    require_json_file_path(path, label=label)


def validate_session_paths(command: DebugRunCommand) -> None:
    reject_unsafe_debug_root(command.session_root, label="session_root")
    reject_unsafe_debug_root(command.output_root, label="output_root")
    if command.session_root.exists() and not command.session_root.is_dir():
        raise ValueError(f"session_root muss ein Verzeichnis sein: {command.session_root}")
    if command.output_root.exists() and not command.output_root.is_dir():
        raise ValueError(f"output_root muss ein Verzeichnis sein: {command.output_root}")


def reject_unsafe_debug_root(path, *, label: str) -> None:
    resolved = Path(path).resolve(strict=False)
    if resolved.name.lower() in FORBIDDEN_DEBUG_ROOT_NAMES or looks_like_module_root(resolved):
        raise ValueError(f"{label} darf nicht auf config/, runtime/, vendor/ oder den Modulroot zeigen: {path}")
    for parent in resolved.parents:
        if parent.name.lower() in FORBIDDEN_DEBUG_ROOT_NAMES and looks_like_module_root(parent.parent):
            raise ValueError(f"{label} darf nicht auf config/, runtime/, vendor/ oder den Modulroot zeigen: {path}")
        if looks_like_module_root(parent):
            break


def looks_like_module_root(path) -> bool:
    candidate = Path(path)
    return (
        (candidate / "normalizer_vision").exists()
        and (candidate / "config").exists()
        and ((candidate / "module-manifest.json").exists() or (candidate / "pyproject.toml").exists())
    )
