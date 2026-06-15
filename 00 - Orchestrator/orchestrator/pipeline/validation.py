"""Hard validation and managed-path guards for pipeline runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import UiState
from . import debug


def ensure_valid_ui_state(ui_state: UiState) -> None:
    if not ui_state.input_folder:
        raise ValueError("Input Folder is not set.")
    if not Path(ui_state.input_folder).exists():
        raise ValueError(f"Input Folder does not exist: {ui_state.input_folder}")
    for label, value in (
        ("Artifact Folder", ui_state.artifact_folder),
        ("Database Storage Folder", ui_state.corpus_output_folder),
        ("Selected Database", getattr(ui_state, "selected_corpus_db_path", "")),
    ):
        if not value:
            raise ValueError(f"{label} is not set.")
    _ensure_selected_database_within_storage(ui_state)
    if getattr(ui_state, "semantic_release_mode", "database_default") == "override_selected":
        release_text = str(ui_state.semantic_release_path or "").strip()
        release_path = Path(release_text)
        if not release_text or not release_path.exists() or not release_path.is_file():
            raise ValueError(f"Semantic Release is missing: {release_path}")


def ensure_valid_release_activation_state(ui_state: UiState) -> None:
    if getattr(ui_state, "semantic_release_mode", "database_default") != "override_selected":
        raise ValueError("Release override mode is not active.")
    release_text = str(ui_state.semantic_release_path or "").strip()
    if not release_text:
        raise ValueError("Semantic Release is not set.")
    release_path = Path(release_text)
    if not release_path.exists() or not release_path.is_file():
        raise ValueError(f"Semantic Release is missing: {release_path}")
    for label, value in (
        ("Selected Database", getattr(ui_state, "selected_corpus_db_path", "")),
    ):
        if not str(value).strip():
            raise ValueError(f"{label} is not set.")
    _ensure_selected_database_within_storage(ui_state)


def ensure_valid_create_database_state(ui_state: UiState) -> None:
    for label, value in (
        ("Database Storage Folder", ui_state.corpus_output_folder),
        ("Selected Database", getattr(ui_state, "selected_corpus_db_path", "")),
    ):
        if not str(value).strip():
            raise ValueError(f"{label} is not set.")
    _ensure_selected_database_within_storage(ui_state)


def resolved_path(path: Path) -> Path:
    try:
        return path.resolve()
    except Exception:
        return path


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def is_managed_path(path: Path, managed_roots: tuple[Path, ...]) -> bool:
    resolved = resolved_path(path)
    return any(is_within(resolved, root) for root in managed_roots)


def ensure_managed_path(
    engine: Any,
    path: Path,
    managed_roots: tuple[Path, ...],
    *,
    action: str,
    noun: str,
) -> bool:
    if is_managed_path(path, managed_roots):
        return True
    debug.append_log(engine, f"[SECURITY] {action}: external {noun} ignored: {path}")
    return False


def validated_existing_file_path(
    engine: Any,
    path_value: str | Path | None,
    *,
    allowed_roots: tuple[Path, ...],
    action: str,
    noun: str,
    missing_message: str,
) -> tuple[Path | None, str]:
    path_text = str(path_value or "").strip()
    if not path_text:
        return None, missing_message
    path = Path(path_text)
    if not ensure_managed_path(engine, path, allowed_roots, action=action, noun=noun):
        return None, f"{noun} is outside the pipeline: {path}"
    if not path.exists() or not path.is_file():
        return None, f"{noun} is missing: {path}"
    return path, ""


def _ensure_selected_database_within_storage(ui_state: UiState) -> None:
    storage_text = str(ui_state.corpus_output_folder or "").strip()
    db_text = str(getattr(ui_state, "selected_corpus_db_path", "") or "").strip()
    if not storage_text or not db_text:
        return
    storage_path = Path(storage_text).resolve()
    selected_db_path = Path(db_text).resolve()
    try:
        selected_db_path.relative_to(storage_path)
    except ValueError as exc:
        raise ValueError("Selected Database must be inside Database Storage Folder.") from exc
