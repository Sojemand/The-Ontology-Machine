from __future__ import annotations

from pathlib import Path

from normalizer_vision.semantic_release import default_publish_output_path, publish_semantic_release


def test_publish_semantic_release_budgets_long_default_file_name(tmp_project_root: Path) -> None:
    release_id = "release_" + "x" * 100
    release_version = "2026." + "y" * 140
    release = publish_semantic_release(
        tmp_project_root,
        release_id=release_id,
        release_version=release_version,
        target_locale="en",
    )
    output_path = default_publish_output_path(
        tmp_project_root,
        release["release_id"],
        release_version=release["release_version"],
        runtime_locale=release["runtime_locale"],
    )

    assert output_path.exists()
    assert len(str(output_path)) <= 259
    assert output_path.name.endswith(".json")
    assert "y" * 120 not in output_path.name
