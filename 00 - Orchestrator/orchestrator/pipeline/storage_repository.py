"""Storage and state persistence for orchestrator pipeline runs."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import policy_store
from ..locking import FileLock, FileLockBusyError
from ..models import UiState, utc_now_iso
from ..state import load_pipeline_state, save_pipeline_state
from . import policy, route_policy
from .exceptions import OrchestratorBusyError
from .validation import resolved_path

_CORPUS_DIR_NAME = "Corpus"


@dataclass
class RunContext:
    ui_state: UiState
    run_id: str
    runtime_dir: Path
    run_log_path: Path
    tracked_hashes: set[str]
    managed_roots: tuple[Path, ...]
    runtime_semantics: object | None = None


def configure_storage(engine: Any, ui_state: UiState) -> None:
    if engine._pipeline_state_override is not None:
        state_dir = engine._pipeline_state_override.parent
        pipeline_state_path = engine._pipeline_state_override
    else:
        state_dir = pipeline_state_dir(engine)
        pipeline_state_path = state_dir / "pipeline_state.json"
    engine._state_dir = state_dir
    engine._runtime_root = state_dir / policy_store.run_workspace_dir_name()
    engine._pipeline_state_path = pipeline_state_path
    ensure_artifact_layout(ui_state)


def pipeline_state_dir(engine: Any) -> Path:
    return engine._project_state_dir / policy_store.pipeline_state_dir_name()


def ensure_artifact_layout(ui_state: UiState) -> None:
    base_root = artifact_root(ui_state)
    if not str(base_root).strip():
        return
    corpus_root(ui_state).mkdir(parents=True, exist_ok=True)
    for route_family in route_layout():
        route_root = route_artifact_root(ui_state, route_family)
        for publication_key in policy_store.route_artifact_subdirs():
            publication_root(route_root, publication_key).mkdir(parents=True, exist_ok=True)
    error_root(ui_state).mkdir(parents=True, exist_ok=True)


def save_state(engine: Any) -> None:
    lock = getattr(engine, "_runtime_lock", None)
    if lock is None:
        engine._state.updated_at = utc_now_iso()
        save_pipeline_state(engine._pipeline_state_path, engine._state)
        return
    with lock:
        engine._state.updated_at = utc_now_iso()
        save_pipeline_state(engine._pipeline_state_path, engine._state)


def reload_state(engine: Any) -> None:
    lock = getattr(engine, "_runtime_lock", None)
    if lock is None:
        engine._state = load_pipeline_state(engine._pipeline_state_path)
        return
    with lock:
        engine._state = load_pipeline_state(engine._pipeline_state_path)


@contextmanager
def mutation_lock(engine: Any, action: str):
    lock = FileLock(engine._lock_path)
    try:
        lock.acquire()
    except FileLockBusyError as exc:
        raise OrchestratorBusyError(
            f"{action} nicht moeglich: Ein anderer Orchestrator-Lauf ist bereits aktiv."
        ) from exc
    try:
        yield
    finally:
        lock.release()


def managed_roots(engine: Any, ui_state: UiState) -> tuple[Path, ...]:
    roots = [engine._state_dir]
    for value in (ui_state.input_folder, ui_state.artifact_folder, str(corpus_root(ui_state))):
        if value.strip():
            roots.append(Path(value))
    return tuple(resolved_path(root) for root in roots)


def artifact_root(ui_state: UiState) -> Path:
    if not ui_state.artifact_folder.strip():
        return Path()
    return Path(ui_state.artifact_folder)


def corpus_root(ui_state: UiState) -> Path:
    selected_db_text = str(getattr(ui_state, "selected_corpus_db_path", "") or "").strip()
    if selected_db_text:
        return Path(selected_db_text).parent
    base_root = artifact_root(ui_state)
    if str(base_root).strip():
        return base_root / _CORPUS_DIR_NAME
    if not ui_state.corpus_output_folder.strip():
        return Path()
    return Path(ui_state.corpus_output_folder)


def corpus_db_path(ui_state: UiState) -> Path:
    selected_db_text = str(getattr(ui_state, "selected_corpus_db_path", "") or "").strip()
    if selected_db_text:
        return Path(selected_db_text)
    root = corpus_root(ui_state)
    if not str(root).strip():
        return Path("corpus.db")
    return root / "corpus.db"


def route_layout() -> dict[str, str]:
    return policy_store.route_folder_map()


def publication_root(base_root: Path, publication_key: str) -> Path:
    return base_root / policy_store.publication_name(publication_key)


def route_folder_name(route_family: str) -> str:
    route_name = str(route_family or "").strip()
    if not route_name:
        return ""
    if route_name == policy_store.unrouted_error_family():
        return route_name
    return route_layout().get(route_name, policy.safe_file_name(route_name))


def route_artifact_root(ui_state: UiState, route_family: str) -> Path:
    base_root = artifact_root(ui_state)
    route_name = route_folder_name(route_family)
    if not route_name:
        return base_root
    return base_root / route_name


def route_logs_root(ui_state: UiState, route_family: str) -> Path:
    return publication_root(route_artifact_root(ui_state, route_family), "logs")


def error_root(ui_state: UiState) -> Path:
    return artifact_root(ui_state) / policy_store.error_root_name()


def legacy_error_root(ui_state: UiState) -> Path:
    roots = legacy_error_roots(ui_state)
    return roots[0] if roots else artifact_root(ui_state)


def legacy_error_roots(ui_state: UiState) -> tuple[Path, ...]:
    return tuple(artifact_root(ui_state) / name for name in policy_store.legacy_error_root_names())


def error_case_route_root(ui_state: UiState, module_name: str, route_family: str) -> Path:
    route_name = route_folder_name(route_policy.bundle_route_family(route_family))
    module_folder = policy.safe_file_name(module_name or "Unknown Module")
    return error_root(ui_state) / module_folder / route_name
