"""Types shared between UI stages."""
from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from ..models import UiState
from ..worker.actions import ACTIVATE_RELEASE_ACTION as ACTIVATE_RELEASE_WORKER_ACTION
from ..worker.actions import CREATE_DATABASE_ACTION as CREATE_DATABASE_WORKER_ACTION
from ..worker.actions import RESET_ACTION as RESET_WORKER_ACTION
from ..worker.actions import RESET_PIPELINE_LOGS_ACTION as RESET_PIPELINE_LOGS_WORKER_ACTION
from ..worker.actions import RUN_ACTION as RUN_WORKER_ACTION

WorkerAction = Literal["run", "reset", "reset_pipeline_logs", "activate_release", "create_database"]
WorkerEventKind = Literal["snapshot", "log", "done", "cancelled", "error"]
WorkerQueueItem = tuple[WorkerEventKind, object]


class EntryLike(Protocol):
    def get(self) -> str: ...
    def delete(self, start: Any, end: Any) -> None: ...
    def insert(self, index: Any, text: str) -> None: ...


@dataclass(frozen=True)
class UiFieldValues:
    input_folder: str = ""
    artifact_folder: str = ""
    semantic_release_path: str = ""
    corpus_output_folder: str = ""
    selected_corpus_db_path: str = ""
    semantic_release_mode: str = "database_default"
    new_database_name: str = ""
    new_database_bootstrap_mode: str = "default_release"
    new_database_taxonomy_locale: str = ""
    mode: str = "batch"

    def to_ui_state(self) -> UiState:
        return UiState.from_dict(
            {
                "input_folder": self.input_folder,
                "artifact_folder": self.artifact_folder,
                "semantic_release_path": self.semantic_release_path,
                "corpus_output_folder": self.corpus_output_folder,
                "selected_corpus_db_path": self.selected_corpus_db_path,
                "semantic_release_mode": self.semantic_release_mode,
                "new_database_name": self.new_database_name,
                "new_database_bootstrap_mode": self.new_database_bootstrap_mode,
                "new_database_taxonomy_locale": self.new_database_taxonomy_locale,
                "mode": self.mode,
            }
        )

    @classmethod
    def from_ui_state(cls, state: UiState) -> "UiFieldValues":
        return cls(
            input_folder=state.input_folder,
            artifact_folder=state.artifact_folder,
            semantic_release_path=state.semantic_release_path,
            corpus_output_folder=state.corpus_output_folder,
            selected_corpus_db_path=state.selected_corpus_db_path,
            semantic_release_mode=state.semantic_release_mode,
            new_database_name=state.new_database_name,
            new_database_bootstrap_mode=state.new_database_bootstrap_mode,
            new_database_taxonomy_locale=state.new_database_taxonomy_locale,
            mode=state.mode,
        )


@dataclass
class WorkerResources:
    process: mp.Process | None = None
    queue: Any | None = None
    cancel_event: Any | None = None
