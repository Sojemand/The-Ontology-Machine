from __future__ import annotations

from pathlib import Path

from corpus_builder.standalone_artifacts.artifact_tree_contract import validate_artifact_tree


def _make_tree(root: Path) -> None:
    for relative in (
        "Input",
        "Corpus",
        "Semantic Release",
        "Documents/logs",
        "Documents/normalized",
        "Documents/originals",
        "Documents/page_images",
        "Documents/raw_extracts",
        "Documents/requests",
        "Documents/structured",
        "Documents/validation",
        "Error Cases",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)


def test_corpus_builder_validates_kernel_artifact_tree(tmp_path: Path) -> None:
    root = tmp_path / "Artifact Tree"
    _make_tree(root)

    result = validate_artifact_tree({"artifact_root_path": str(root), "target_identity": {}})

    assert result["status"] == "ok"
    assert result["output_refs"]["is_valid"] is True


def test_corpus_builder_detects_missing_folder(tmp_path: Path) -> None:
    root = tmp_path / "Artifact Tree"
    _make_tree(root)
    (root / "Input").rmdir()

    result = validate_artifact_tree({"artifact_root_path": str(root), "target_identity": {}})

    assert result["output_refs"]["is_valid"] is False
    assert "Input" in result["output_refs"]["missing_paths"]
