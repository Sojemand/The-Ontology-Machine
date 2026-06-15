from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .tool_handler_deps import ToolFailure, _optional_bool, _optional_text, _positive_int, _read_active_orchestrator_ui_state, _validate_active_pipeline_state

MAX_SAMPLE_SET_FILES = 50
_INTAKE_POLICY_PATH = Path(__file__).resolve().parents[2] / "00 - Orchestrator" / "config" / "route_intake_policy.json"
_INTAKE_SUFFIX_CACHE: tuple[int, int, tuple[str, ...]] | None = None


def sample_set_limit(arguments: dict[str, Any]) -> int:
    return min(_positive_int(arguments.get("max_samples", 20), "max_samples"), MAX_SAMPLE_SET_FILES)


def active_input_folder_sample_paths(arguments: dict[str, Any]) -> list[Path]:
    result = _dedupe_paths([path.expanduser().resolve() for path in _input_folder_paths(sample_set_limit(arguments))])
    if not result:
        raise ToolFailure("Der aktive Input-Folder enthaelt keine unterstuetzten Beispieldateien.")
    return result[:sample_set_limit(arguments)]


def source_sample_paths(arguments: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    paths.extend(_explicit_paths(arguments.get("source_document_paths")))
    single = _optional_text(arguments, "source_document_path")
    if single:
        paths.append(Path(single))
    folder = _optional_text(arguments, "sample_folder")
    if folder:
        paths.extend(_folder_paths(Path(folder), sample_set_limit(arguments)))
    if _optional_bool(arguments, "include_input_folder", default=False):
        paths.extend(_input_folder_paths(sample_set_limit(arguments)))
    result = _dedupe_paths([path.expanduser().resolve() for path in paths])
    if not result:
        raise ToolFailure("Bitte nenne Sample-Dateien, einen Sample-Ordner oder erlaube den aktiven Input-Folder als Sample-Set.")
    return result[:sample_set_limit(arguments)]


def _explicit_paths(value: Any) -> list[Path]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ToolFailure("source_document_paths muss eine Liste von Dateipfaden sein.")
    paths = []
    for item in value:
        text = str(item or "").strip()
        if text:
            paths.append(Path(text))
    return paths


def _folder_paths(folder: Path, limit: int) -> list[Path]:
    root = folder.expanduser().resolve()
    if not root.is_dir():
        raise ToolFailure(f"Sample-Ordner ist nicht lesbar: {root}")
    suffixes = supported_suffixes()
    return [path for path in sorted(root.rglob("*")) if path.is_file() and _is_supported(path, suffixes)][:limit]


def _input_folder_paths(limit: int) -> list[Path]:
    ui_state = _read_active_orchestrator_ui_state()
    _validate_active_pipeline_state(ui_state)
    input_root = Path(str(ui_state["input_folder"])).expanduser().resolve()
    if not input_root.is_dir():
        raise ToolFailure(f"Aktiver Input-Folder ist nicht lesbar: {input_root}")
    suffixes = supported_suffixes()
    return [path for path in sorted(input_root.rglob("*")) if path.is_file() and _is_supported(path, suffixes)][:limit]


def supported_suffixes() -> tuple[str, ...]:
    suffixes = pipeline_intake_suffixes()
    return suffixes or (".pdf", ".txt", ".md", ".doc", ".docx", ".odt", ".rtf", ".jpg", ".jpeg", ".png")


def _is_supported(path: Path, suffixes: tuple[str, ...]) -> bool:
    return path.suffix.casefold() in set(suffixes)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path).casefold()
        if key not in seen:
            result.append(path)
            seen.add(key)
    return result


def pipeline_intake_suffixes() -> tuple[str, ...]:
    global _INTAKE_SUFFIX_CACHE
    try:
        stat = _INTAKE_POLICY_PATH.stat()
    except OSError:
        return ()
    cached = _INTAKE_SUFFIX_CACHE
    if cached is not None and cached[:2] == (stat.st_mtime_ns, stat.st_size):
        return cached[2]
    try:
        payload = json.loads(_INTAKE_POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    groups = payload.get("suffix_groups") if isinstance(payload, dict) else {}
    suffixes = sorted(
        {
            str(item).casefold()
            for values in (groups.values() if isinstance(groups, dict) else [])
            if isinstance(values, list)
            for item in values
            if isinstance(item, str) and item.startswith(".")
        },
        key=len,
        reverse=True,
    )
    _INTAKE_SUFFIX_CACHE = (stat.st_mtime_ns, stat.st_size, tuple(suffixes))
    return tuple(suffixes)


__all__ = [name for name in globals() if not name.startswith("__")]
