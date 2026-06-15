"""UI state types for orchestrator persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .coercion import coerce_str

_CORPUS_DIR_NAME = "Corpus"


@dataclass
class UiState:
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

    def __post_init__(self) -> None:
        self.mode = self.mode if self.mode in {"batch", "single"} else "batch"
        self.semantic_release_mode = (
            self.semantic_release_mode
            if self.semantic_release_mode in {"database_default", "override_selected"}
            else "database_default"
        )
        self.new_database_bootstrap_mode = (
            self.new_database_bootstrap_mode
            if self.new_database_bootstrap_mode in {"default_release", "no_release"}
            else "default_release"
        )
        self.new_database_taxonomy_locale = str(self.new_database_taxonomy_locale or "").strip().lower()
        self.corpus_output_folder = _canonical_corpus_output_folder(
            artifact_folder=self.artifact_folder,
            corpus_output_folder=self.corpus_output_folder,
        )
        self.selected_corpus_db_path = _canonical_selected_corpus_db_path(
            artifact_folder=self.artifact_folder,
            corpus_output_folder=self.corpus_output_folder,
            selected_corpus_db_path=self.selected_corpus_db_path,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UiState":
        mode = coerce_str(data.get("mode", "batch"), "batch").strip().lower() or "batch"
        if mode not in {"batch", "single"}:
            mode = "batch"
        artifact_folder = coerce_str(data.get("artifact_folder", "")).strip()
        corpus_output_folder = _canonical_corpus_output_folder(
            artifact_folder=artifact_folder,
            corpus_output_folder=coerce_str(data.get("corpus_output_folder", "")).strip(),
        )
        selected_corpus_db_path = _canonical_selected_corpus_db_path(
            artifact_folder=artifact_folder,
            corpus_output_folder=corpus_output_folder,
            selected_corpus_db_path=coerce_str(data.get("selected_corpus_db_path", "")).strip(),
        )
        semantic_release_mode = coerce_str(data.get("semantic_release_mode", "database_default"), "database_default").strip().lower() or "database_default"
        if semantic_release_mode not in {"database_default", "override_selected"}:
            semantic_release_mode = "database_default"
        new_database_bootstrap_mode = coerce_str(data.get("new_database_bootstrap_mode", "default_release"), "default_release").strip().lower() or "default_release"
        if new_database_bootstrap_mode not in {"default_release", "no_release"}:
            new_database_bootstrap_mode = "default_release"
        return cls(
            input_folder=coerce_str(data.get("input_folder", "")).strip(),
            artifact_folder=artifact_folder,
            semantic_release_path=coerce_str(data.get("semantic_release_path", "")).strip(),
            corpus_output_folder=corpus_output_folder,
            selected_corpus_db_path=selected_corpus_db_path,
            semantic_release_mode=semantic_release_mode,
            new_database_name=coerce_str(data.get("new_database_name", "")).strip(),
            new_database_bootstrap_mode=new_database_bootstrap_mode,
            new_database_taxonomy_locale=coerce_str(data.get("new_database_taxonomy_locale", "")).strip().lower(),
            mode=mode,
        )


def _canonical_corpus_output_folder(*, artifact_folder: str, corpus_output_folder: str) -> str:
    if corpus_output_folder:
        return corpus_output_folder
    if artifact_folder:
        return str(Path(artifact_folder) / _CORPUS_DIR_NAME)
    return ""


def _canonical_selected_corpus_db_path(
    *,
    artifact_folder: str,
    corpus_output_folder: str,
    selected_corpus_db_path: str,
) -> str:
    if selected_corpus_db_path:
        return selected_corpus_db_path
    if corpus_output_folder:
        return str(Path(corpus_output_folder) / "corpus.db")
    if artifact_folder:
        return str(Path(artifact_folder) / _CORPUS_DIR_NAME / "corpus.db")
    return ""
