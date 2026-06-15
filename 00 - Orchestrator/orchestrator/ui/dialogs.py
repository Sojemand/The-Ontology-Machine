"""Tk dialog boundary for the Orchestrator desktop UI."""

from __future__ import annotations

from .dialogs_artifact_tree import prompt_create_artifact_tree
from .dialogs_basic import (
    confirm_release_activation,
    confirm_reset,
    confirm_reset_debug_output,
    confirm_reset_pipeline_logs,
    select_artifact_folder,
    select_corpus_folder,
    select_database_file,
    select_debug_artifact_dir,
    select_debug_artifact_file,
    select_debug_input_path,
    select_debug_source_path,
    select_input_folder,
    select_release_file,
    show_error,
)
from .dialogs_database import (
    _canonical_create_database_blueprint,
    _format_locale_label,
    prompt_create_database,
)
from .dialogs_info import _info_window_subtitle, show_info_window

__all__ = [
    "_canonical_create_database_blueprint",
    "_format_locale_label",
    "_info_window_subtitle",
    "confirm_release_activation",
    "confirm_reset",
    "confirm_reset_debug_output",
    "confirm_reset_pipeline_logs",
    "prompt_create_artifact_tree",
    "prompt_create_database",
    "select_artifact_folder",
    "select_corpus_folder",
    "select_database_file",
    "select_debug_artifact_dir",
    "select_debug_artifact_file",
    "select_debug_input_path",
    "select_debug_source_path",
    "select_input_folder",
    "select_release_file",
    "show_error",
    "show_info_window",
]
