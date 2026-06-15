"""Corpus-context activation for the orchestrator contract surface."""

from __future__ import annotations

from pathlib import Path

from ..locking import FileLock, FileLockBusyError
from ..pipeline.validation import is_within


def activate_corpus_context_action(
    command: dict[str, str],
    *,
    root: Path,
    ui_state_cls,
    load_ui_state,
    save_ui_state,
) -> dict:
    state_dir = Path(root) / "state"
    state_path = state_dir / "ui_state.json"
    lock_path = state_dir / "orchestrator.lock"
    corpus_db_path = Path(command["corpus_db_path"]).expanduser().resolve()
    _require_file(corpus_db_path, "Corpus DB")

    storage_path = Path(command.get("corpus_output_folder") or corpus_db_path.parent).expanduser().resolve()
    _require_dir(storage_path, "Database Storage Folder")
    if not is_within(corpus_db_path, storage_path):
        raise ValueError("Corpus DB must be inside Database Storage Folder.")

    artifact_path = _optional_artifact_path(command)
    if artifact_path and not is_within(storage_path, artifact_path):
        raise ValueError("Database Storage Folder must be inside Artifact Folder.")

    input_path = _optional_input_path(command, artifact_path)
    updated, previous = _save_corpus_context(
        state_path=state_path,
        lock_path=lock_path,
        ui_state_cls=ui_state_cls,
        load_ui_state=load_ui_state,
        save_ui_state=save_ui_state,
        artifact_path=artifact_path,
        input_path=input_path,
        storage_path=storage_path,
        corpus_db_path=corpus_db_path,
    )
    return {
        "status": "ok",
        "artifact_folder": updated.artifact_folder,
        "input_folder": updated.input_folder,
        "corpus_db_path": updated.selected_corpus_db_path,
        "corpus_output_folder": updated.corpus_output_folder,
        "semantic_release_mode": updated.semantic_release_mode,
        "previous_input_folder": str(previous.get("input_folder") or ""),
        "previous_artifact_folder": str(previous.get("artifact_folder") or ""),
        "previous_corpus_db_path": str(previous.get("selected_corpus_db_path") or ""),
        "previous_corpus_output_folder": str(previous.get("corpus_output_folder") or ""),
    }


def _optional_artifact_path(command: dict[str, str]) -> Path | None:
    artifact_text = str(command.get("artifact_folder") or "").strip()
    if not artifact_text:
        return None
    artifact_path = Path(artifact_text).expanduser().resolve()
    _require_dir(artifact_path, "Artifact Folder")
    return artifact_path


def _optional_input_path(command: dict[str, str], artifact_path: Path | None) -> Path | None:
    input_text = str(command.get("input_folder") or "").strip()
    if not input_text:
        return None
    input_path = Path(input_text).expanduser().resolve()
    _require_dir(input_path, "Input Folder")
    if artifact_path and not is_within(input_path, artifact_path):
        raise ValueError("Input Folder must be inside Artifact Folder.")
    return input_path


def _save_corpus_context(
    *,
    state_path: Path,
    lock_path: Path,
    ui_state_cls,
    load_ui_state,
    save_ui_state,
    artifact_path: Path | None,
    input_path: Path | None,
    storage_path: Path,
    corpus_db_path: Path,
):
    lock = FileLock(lock_path)
    try:
        lock.acquire()
    except FileLockBusyError as exc:
        raise RuntimeError("Corpus context cannot be activated: Orchestrator is busy.") from exc
    try:
        current = load_ui_state(state_path)
        previous = current.to_dict()
        updated = ui_state_cls.from_dict(
            {
                **previous,
                **({"artifact_folder": str(artifact_path)} if artifact_path else {}),
                **({"input_folder": str(input_path)} if input_path else {}),
                "corpus_output_folder": str(storage_path),
                "selected_corpus_db_path": str(corpus_db_path),
                "semantic_release_mode": "database_default",
                "semantic_release_path": "",
            }
        )
        save_ui_state(state_path, updated)
        return updated, previous
    finally:
        lock.release()


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{label} must be a file: {path}")


def _require_dir(path: Path, label: str) -> None:
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"{label} must be a folder: {path}")
