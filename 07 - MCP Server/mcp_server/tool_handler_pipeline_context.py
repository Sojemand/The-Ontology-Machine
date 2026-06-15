from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .contract_client import module_spec
from .tool_handler_path_checks import _is_within
from .tool_handler_types import ToolFailure

def _record_matches_active_workspace(record: dict[str, Any], input_root: Path, artifact_root: Path) -> bool:
    for key in ("original_source_path", "source_path"):
        path_text = str(record.get(key) or "").strip()
        if not path_text:
            continue
        path = Path(path_text).expanduser().resolve()
        if _is_within(path, input_root) or _is_within(path, artifact_root):
            return True
    return any(_is_within(path.expanduser().resolve(), artifact_root) for path in _record_artifact_paths(record))


def _record_artifact_paths(record: dict[str, Any]) -> list[Path]:
    artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
    paths: list[Path] = []
    for key in (
        "optimizer_raw_paths",
        "optimizer_page_image_paths",
        "interpreter_request_paths",
        "structured_paths",
        "normalized_paths",
        "validation_report_paths",
    ):
        values = artifacts.get(key)
        if isinstance(values, list):
            paths.extend(Path(str(value)) for value in values if str(value or "").strip())
    for key in ("bundle_dir", "bundle_manifest_path", "structured_path", "normalized_path", "validation_report_path"):
        value = str(artifacts.get(key) or "").strip()
        if value:
            paths.append(Path(value))
    return paths


def _orchestrator_ui_state_path() -> Path:
    return module_spec("orchestrator").root / "state" / "ui_state.json"


def _read_active_orchestrator_ui_state() -> dict[str, Any]:
    path = _orchestrator_ui_state_path()
    if not path.exists():
        raise ToolFailure(
            "Es ist noch kein aktiver Pipeline-Kontext gespeichert. "
            "Lege zuerst eine Workspace-DB an oder aktiviere eine bestehende DB."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise ToolFailure(f"Orchestrator UI-State ist nicht lesbar: {path}") from exc
    if not isinstance(payload, dict):
        raise ToolFailure(f"Orchestrator UI-State ist kein JSON-Objekt: {path}")
    return payload


def _validate_active_pipeline_state(ui_state: dict[str, Any]) -> None:
    required = {
        "input_folder": "Input Folder",
        "artifact_folder": "Artefakt Folder",
        "corpus_output_folder": "Database Storage Folder",
        "selected_corpus_db_path": "Selected Database",
    }
    missing = [label for key, label in required.items() if not str(ui_state.get(key) or "").strip()]
    if missing:
        raise ToolFailure(f"Aktiver Pipeline-Kontext ist unvollstaendig: {', '.join(missing)} fehlt.")
    input_path = Path(str(ui_state["input_folder"])).expanduser().resolve()
    artifact_path = Path(str(ui_state["artifact_folder"])).expanduser().resolve()
    corpus_path = Path(str(ui_state["corpus_output_folder"])).expanduser().resolve()
    db_path = Path(str(ui_state["selected_corpus_db_path"])).expanduser().resolve()
    for label, path in (
        ("Input Folder", input_path),
        ("Artefakt Folder", artifact_path),
        ("Database Storage Folder", corpus_path),
    ):
        if not path.exists():
            raise ToolFailure(f"{label} existiert nicht: {path}")
        if not path.is_dir():
            raise ToolFailure(f"{label} muss ein Ordner sein: {path}")
    if not db_path.exists():
        raise ToolFailure(f"Selected Database existiert nicht: {db_path}")
    if not db_path.is_file():
        raise ToolFailure(f"Selected Database muss eine Datei sein: {db_path}")
    if not _is_within(db_path, corpus_path):
        raise ToolFailure("Selected Database muss innerhalb von Database Storage Folder liegen.")


def _pipeline_input_preview(input_folder: str, *, max_items: int) -> dict[str, Any]:
    input_path = Path(input_folder).expanduser().resolve()
    files = sorted(path for path in input_path.rglob("*") if path.is_file())
    preview = []
    for path in files[:max_items]:
        try:
            relative = path.relative_to(input_path).as_posix()
        except ValueError:
            relative = str(path)
        preview.append({"relative_path": relative, "size_bytes": path.stat().st_size})
    return {
        "input_folder": str(input_path),
        "total_files": len(files),
        "preview_count": len(preview),
        "preview_files": preview,
        "truncated": len(files) > len(preview),
    }


def _active_context_summary(ui_state: dict[str, Any]) -> dict[str, str]:
    return {
        "input_folder": str(ui_state.get("input_folder") or ""),
        "artifact_folder": str(ui_state.get("artifact_folder") or ""),
        "corpus_output_folder": str(ui_state.get("corpus_output_folder") or ""),
        "corpus_db_path": str(ui_state.get("selected_corpus_db_path") or ""),
        "semantic_release_mode": str(ui_state.get("semantic_release_mode") or "database_default"),
    }

__all__ = [name for name in globals() if not name.startswith("__")]
