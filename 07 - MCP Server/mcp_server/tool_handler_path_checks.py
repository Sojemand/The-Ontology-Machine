from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from .atomic_io import atomic_json_write
from .tool_handler_runtime_state import PIPELINE_ARTIFACT_DIRS
from .tool_handler_pipeline_store import _state_dir
from .tool_handler_types import ToolFailure
from .tool_handler_validation import _optional_text

WINDOWS_PATH_BUDGET_CHARS = 300

def _corpus_output_folder(arguments: dict[str, Any], corpus_db_path: str) -> str:
    return _optional_text(arguments, "corpus_output_folder") or str(Path(corpus_db_path).expanduser().resolve().parent)


def _validate_existing_context_target(corpus_db_path: str, corpus_output_folder: str) -> None:
    db_path = Path(corpus_db_path).expanduser().resolve()
    storage_path = Path(corpus_output_folder).expanduser().resolve()
    if not db_path.exists():
        raise ToolFailure(f"corpus_db_path existiert nicht: {db_path}")
    if not db_path.is_file():
        raise ToolFailure(f"corpus_db_path muss eine Datei sein: {db_path}")
    _validate_storage_contains_db(db_path, storage_path)


def _validate_new_context_target(corpus_db_path: str, corpus_output_folder: str) -> None:
    db_path = Path(corpus_db_path).expanduser().resolve()
    storage_path = Path(corpus_output_folder).expanduser().resolve()
    if db_path.exists() or db_path.with_name(f"{db_path.name}-wal").exists() or db_path.with_name(f"{db_path.name}-shm").exists():
        raise ToolFailure(f"corpus_db_path existiert bereits: {db_path}")
    _validate_storage_contains_db(db_path, storage_path)


def _validate_storage_contains_db(db_path: Path, storage_path: Path) -> None:
    if not storage_path.exists():
        raise ToolFailure(f"corpus_output_folder existiert nicht: {storage_path}")
    if not storage_path.is_dir():
        raise ToolFailure(f"corpus_output_folder muss ein Ordner sein: {storage_path}")
    if not _is_within(db_path, storage_path):
        raise ToolFailure("corpus_db_path muss innerhalb von corpus_output_folder liegen.")


def _write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    _ensure_path_budget(path, "JSON-Artefaktpfad")
    atomic_json_write(path, payload, indent=2, trailing_newline=True)


def _validate_optional_artifact_root(corpus_output_folder: str, artifact_folder: str) -> None:
    if not artifact_folder:
        return
    artifact_path = Path(artifact_folder).expanduser().resolve()
    storage_path = Path(corpus_output_folder).expanduser().resolve()
    if not artifact_path.exists():
        raise ToolFailure(f"artifact_folder existiert nicht: {artifact_path}")
    if not artifact_path.is_dir():
        raise ToolFailure(f"artifact_folder muss ein Ordner sein: {artifact_path}")
    if not _is_within(storage_path, artifact_path):
        raise ToolFailure("corpus_output_folder muss innerhalb von artifact_folder liegen.")


def _validate_optional_input_folder(input_folder: str, artifact_folder: str) -> None:
    if not input_folder:
        return
    input_path = Path(input_folder).expanduser().resolve()
    if not input_path.exists():
        raise ToolFailure(f"input_folder existiert nicht: {input_path}")
    if not input_path.is_dir():
        raise ToolFailure(f"input_folder muss ein Ordner sein: {input_path}")
    if artifact_folder:
        artifact_path = Path(artifact_folder).expanduser().resolve()
        if not _is_within(input_path, artifact_path):
            raise ToolFailure("input_folder muss innerhalb von artifact_folder liegen.")


def _validate_release_output_path(
    output_path: str,
    *,
    artifact_folder: str = "",
    corpus_output_folder: str = "",
) -> None:
    release_path = Path(output_path).expanduser().resolve()
    _ensure_path_budget(release_path, "release_output_path")
    mcp_release_state = (_state_dir() / "semantic_releases").resolve()
    if _is_within(release_path, mcp_release_state):
        raise ToolFailure(
            "release_output_path darf nicht unter MCP state/semantic_releases liegen. "
            "Nutze einen Workspace-, Corpus- oder expliziten User-Zielpfad."
        )
    if artifact_folder:
        artifact_path = Path(artifact_folder).expanduser().resolve()
        if not _is_within(release_path, artifact_path):
            raise ToolFailure("release_output_path muss innerhalb von artifact_folder liegen.")
    if corpus_output_folder and not release_path.parent.exists():
        raise ToolFailure(f"release_output_path parent existiert nicht: {release_path.parent}")


def _ensure_pipeline_artifact_structure(artifact_path: Path) -> list[str]:
    _ensure_path_budget(artifact_path, "artifact_folder")
    created: list[str] = []
    targets = (Path("."), *PIPELINE_ARTIFACT_DIRS)
    for relative in targets:
        target = artifact_path if relative == Path(".") else artifact_path / relative
        _ensure_path_budget(target, "Pipeline-Artefaktpfad")
        if target.exists() and not target.is_dir():
            raise ToolFailure(f"Pipeline-Artefaktpfad ist kein Ordner: {target}")
        if not target.exists():
            created.append(str(target))
        target.mkdir(parents=True, exist_ok=True)
    return created


def _prepare_workspace_database_target(
    corpus_db_path: Path,
    corpus_root: Path,
    *,
    if_database_exists: str,
) -> str:
    _ensure_path_budget(corpus_db_path, "corpus_db_path")
    if not corpus_db_path.exists():
        _validate_new_context_target(str(corpus_db_path), str(corpus_root))
        return "new"
    _validate_existing_context_target(str(corpus_db_path), str(corpus_root))
    if if_database_exists == "fail":
        raise ToolFailure(f"corpus_db_path existiert bereits: {corpus_db_path}")
    if if_database_exists == "adopt_empty":
        _validate_empty_corpus_db(corpus_db_path)
    return "existing"


def _validate_empty_corpus_db(db_path: Path) -> None:
    try:
        conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            tables = {
                str(row[0])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            }
            if "documents" not in tables:
                return
            row = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
            if int(row[0] if row else 0) == 0:
                return
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise ToolFailure(f"corpus_db_path ist keine lesbare SQLite-DB: {db_path}") from exc
    raise ToolFailure(
        f"corpus_db_path enthaelt bereits Dokumente: {db_path}. "
        "Nutze if_database_exists='adopt_any' nur nach ausdruecklicher Bestaetigung."
    )


def _safe_database_stem(value: str) -> str:
    name = Path(value).name.strip()
    if name.lower().endswith(".db"):
        name = name[:-3]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    if not safe:
        raise ToolFailure("database_name enthaelt keinen gueltigen Dateinamen.")
    return safe


def _ensure_path_budget(path: Path, label: str) -> None:
    path_text = str(path)
    if len(path_text) <= WINDOWS_PATH_BUDGET_CHARS:
        return
    raise ToolFailure(
        f"{label} waere {len(path_text)} Zeichen lang und ueberschreitet das "
        f"Windows-Pfadbudget von {WINDOWS_PATH_BUDGET_CHARS}. "
        "Waehle einen kuerzeren Workspace-Pfad oder Dateinamen."
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

__all__ = [name for name in globals() if not name.startswith("__")]
