from __future__ import annotations

from pathlib import Path

from corpus_builder.semantic_release.multi_source_merge_preflight import multi_source_merge_preflight
from corpus_builder.semantic_release.multi_source_merge_workflow import multi_source_merge_databases

from .multi_source_merge_support import load_artifact_json, selection, source_database


def test_filled_merge_copies_source_artifact_tree_files_without_control_roots(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Merge Root"
    (artifact_root / "Corpus").mkdir(parents=True, exist_ok=True)
    merge_selection = selection(artifact_root, "filled")
    merge_selection["source_databases"][1]["source_state"] = "empty"
    source_database(artifact_root, "db_a", "source_doc_a", "sha256:content_a")
    source_root = Path(merge_selection["source_databases"][0]["source_artifact_root"])
    extra_files = {
        "Documents/raw_extracts/source_doc_a.raw.json": b"raw",
        "Documents/structured/source_doc_a.structured.json": b"structured",
        "Documents/normalized/source_doc_a.normalized.json": b"normalized",
        "Documents/logs/pipeline_batches/batch_a/pipeline_batch_manifest.json": b"batch",
        "Documents/logs/merge_runs/old_merge/merge_selection.json": b"old merge",
        "Error Cases/Validator/source_doc_a/error.json": b"error",
        "Input/pending.pdf": b"pending",
        "Corpus/source.db": b"source db bytes",
        "Semantic Release/releases/source/release.json": b"source release",
    }
    for relative, content in extra_files.items():
        path = source_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    multi_source_merge_preflight({"selection": merge_selection})
    merged = multi_source_merge_databases({"selection": merge_selection, "mode": "additive"})

    artifact_map = load_artifact_json(artifact_root, merged["output_refs"]["artifact_map_ref"])
    copied_targets = {item["target_artifact_path"] for item in artifact_map["mappings"]}
    assert "Documents/raw_extracts/source_doc_a.raw.json" in copied_targets
    assert "Documents/structured/source_doc_a.structured.json" in copied_targets
    assert "Documents/normalized/source_doc_a.normalized.json" in copied_targets
    assert "Documents/logs/pipeline_batches/batch_a/pipeline_batch_manifest.json" in copied_targets
    assert "Documents/logs/imported/db_a/merge_runs/old_merge/merge_selection.json" in copied_targets
    assert "Error Cases/Validator/source_doc_a/error.json" in copied_targets
    assert (artifact_root / "Documents" / "raw_extracts" / "source_doc_a.raw.json").read_bytes() == b"raw"
    imported_manifest = artifact_root / "Documents" / "logs" / "imported" / "db_a" / "merge_runs" / "old_merge" / "merge_selection.json"
    assert imported_manifest.read_bytes() == b"old merge"
    assert "Input/pending.pdf" not in copied_targets
    assert "Corpus/source.db" not in copied_targets
    assert "Semantic Release/releases/source/release.json" not in copied_targets


def test_filled_merge_maps_legacy_external_document_paths_to_tree_originals(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Merge Root"
    (artifact_root / "Corpus").mkdir(parents=True, exist_ok=True)
    merge_selection = selection(artifact_root, "filled")
    source_database(
        artifact_root,
        "db_a",
        "source_doc_a",
        "sha256:content_a",
        stored_file_path="../../source/source_doc_a.pdf",
    )
    source_database(artifact_root, "db_b", "source_doc_b", "sha256:content_b")

    preflight = multi_source_merge_preflight({"selection": merge_selection})
    merged = multi_source_merge_databases({"selection": merge_selection, "mode": "filled_sql_and_artifacts"})

    assert preflight["status"] == "ok"
    id_map = load_artifact_json(artifact_root, merged["output_refs"]["merge_id_map_ref"])["mappings"]
    legacy_mapping = next(item for item in id_map if item["source_document_id"] == "source_doc_a")
    assert legacy_mapping["source_artifact_path"] == "Documents/originals/source_doc_a.pdf"
    assert Path(legacy_mapping["target_artifact_path"]).as_posix().startswith("Documents/originals/")
    assert Path(artifact_root / legacy_mapping["target_artifact_path"]).is_file()
