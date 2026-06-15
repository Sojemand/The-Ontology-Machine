from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.ui import validation
from orchestrator.ui.types import UiFieldValues


def test_can_start_requires_mandatory_paths_and_idle_state() -> None:
    ready = UiFieldValues(
        input_folder="input",
        artifact_folder="artifacts",
        corpus_output_folder="corpus",
        selected_corpus_db_path="corpus\\test.db",
    )

    assert validation.can_start(ready, processing=False) is True
    assert validation.can_start(ready, processing=True) is False
    assert validation.can_start(UiFieldValues(input_folder="input", corpus_output_folder="corpus"), processing=False) is False


def test_ensure_startable_lists_all_missing_fields() -> None:
    with pytest.raises(ValueError, match="Input Folder, Artifact Folder, Database Storage Folder, Selected Database"):
        validation.ensure_startable(UiFieldValues())


def test_release_activation_requires_release_file_and_corpus_folder(tmp_path: Path) -> None:
    release_path = tmp_path / "semantic_release.json"
    release_path.write_text("{}", encoding="utf-8")
    storage_dir = tmp_path / "corpus"
    selected_db_path = storage_dir / "selected.db"
    ready = UiFieldValues(
        semantic_release_path=str(release_path),
        corpus_output_folder=str(storage_dir),
        selected_corpus_db_path=str(selected_db_path),
        semantic_release_mode="override_selected",
    )

    assert validation.can_activate_release(ready, processing=False) is True
    assert validation.can_activate_release(ready, processing=True) is False
    with pytest.raises(ValueError, match="Release Override Mode, Semantic Release, Selected Database"):
        validation.ensure_release_activation_ready(UiFieldValues())
