from __future__ import annotations

from semantic_control_kernel.workflows.database_creation.interaction_helpers import (
    CreationTargetProgress as _CreationTargetProgress,
    clean_path as _clean_path,
    prefilled_values_for as _prefilled_values_for,
    summary_for as _summary_for,
)


def test_name_artifact_root_folder_uses_name_prompt_and_default() -> None:
    progress = _CreationTargetProgress(artifact_root_parent_path=r"C:\Users\Norma\Desktop\File Optimizer")

    assert _summary_for("name_artifact_root_folder", progress) == "Enter the name for the new Artifact Tree root folder."
    assert _prefilled_values_for("name_artifact_root_folder", progress) == {"text_value": "Artifact Tree"}


def test_clean_path_strips_wrapping_quotes() -> None:
    cleaned = _clean_path('"C:\\Users\\Norma\\Desktop\\File Optimizer"')

    assert cleaned is not None
    assert '"' not in cleaned
    assert cleaned.endswith(r"Users\Norma\Desktop\File Optimizer")
