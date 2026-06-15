"""Hard UI invariants for startable orchestrator runs."""
from __future__ import annotations

from pathlib import Path

from .types import UiFieldValues

_REQUIRED_FIELDS = (
    ("Input Folder", "input_folder"),
    ("Artifact Folder", "artifact_folder"),
    ("Database Storage Folder", "corpus_output_folder"),
    ("Selected Database", "selected_corpus_db_path"),
)


def missing_required_fields(fields: UiFieldValues) -> list[str]:
    return [label for label, attr in _REQUIRED_FIELDS if not getattr(fields, attr).strip()]


def can_start(fields: UiFieldValues, processing: bool) -> bool:
    if processing or missing_required_fields(fields):
        return False
    if _selected_database_outside_storage(fields):
        return False
    if fields.semantic_release_mode == "override_selected" and not Path(fields.semantic_release_path.strip()).is_file():
        return False
    return True


def can_activate_release(fields: UiFieldValues, processing: bool) -> bool:
    if processing:
        return False
    if fields.semantic_release_mode != "override_selected":
        return False
    if missing_release_activation_fields(fields):
        return False
    release_path = Path(fields.semantic_release_path.strip())
    return release_path.exists() and release_path.is_file()


def can_create_database(fields: UiFieldValues, processing: bool) -> bool:
    return not processing and bool(str(fields.corpus_output_folder or "").strip())


def ensure_startable(fields: UiFieldValues) -> None:
    missing = missing_required_fields(fields)
    if missing:
        raise ValueError(f"Set first: {', '.join(missing)}")
    outside_storage = _selected_database_outside_storage(fields)
    if outside_storage:
        raise ValueError(outside_storage)
    if fields.semantic_release_mode == "override_selected":
        release_path = Path(fields.semantic_release_path.strip())
        if not release_path.exists() or not release_path.is_file():
            raise ValueError(f"Semantic Release is missing: {release_path}")


def missing_release_activation_fields(fields: UiFieldValues) -> list[str]:
    missing: list[str] = []
    if fields.semantic_release_mode != "override_selected":
        missing.append("Release Override Mode")
    if not fields.semantic_release_path.strip():
        missing.append("Semantic Release")
    if not fields.selected_corpus_db_path.strip():
        missing.append("Selected Database")
    return missing


def ensure_release_activation_ready(fields: UiFieldValues) -> None:
    missing = missing_release_activation_fields(fields)
    if missing:
        raise ValueError(f"Set first: {', '.join(missing)}")
    outside_storage = _selected_database_outside_storage(fields)
    if outside_storage:
        raise ValueError(outside_storage)
    release_path = Path(fields.semantic_release_path.strip())
    if not release_path.exists() or not release_path.is_file():
        raise ValueError(f"Semantic Release is missing: {release_path}")


def ensure_create_database_ready(fields: UiFieldValues) -> None:
    if not str(fields.corpus_output_folder or "").strip():
        raise ValueError("Set first: Database Storage Folder")


def _selected_database_outside_storage(fields: UiFieldValues) -> str:
    storage_text = str(fields.corpus_output_folder or "").strip()
    db_text = str(fields.selected_corpus_db_path or "").strip()
    if not storage_text or not db_text:
        return ""
    try:
        Path(db_text).resolve().relative_to(Path(storage_text).resolve())
    except Exception:
        return "Selected Database must be inside Database Storage Folder."
    return ""
