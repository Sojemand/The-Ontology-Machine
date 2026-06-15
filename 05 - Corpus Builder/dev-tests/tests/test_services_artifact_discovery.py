"""Standalone artifact discovery tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from corpus_builder.context import ModuleContext
from corpus_builder.standalone_artifacts import build_rebuild_bundles_from_artifacts


def test_build_rebuild_bundles_from_artifacts_scans_normalized_and_sidecars(
    tmp_path: Path,
    vision_structured,
    vision_validation_report,
    vision_normalized,
):
    context = ModuleContext(tmp_path)
    pipeline_root = tmp_path / "pipeline"
    normalized_dir = pipeline_root / "normalized" / "finance"
    structured_dir = pipeline_root / "structured" / "finance"
    validation_dir = pipeline_root / "validation" / "finance"
    normalized_dir.mkdir(parents=True)
    structured_dir.mkdir(parents=True)
    validation_dir.mkdir(parents=True)

    (normalized_dir / "invoice.pdf.structured.normalized.json").write_text(
        json.dumps(vision_normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (structured_dir / "invoice.pdf.structured.json").write_text(
        json.dumps(vision_structured, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (validation_dir / "invoice.pdf.vision_validation_report.json").write_text(
        json.dumps(vision_validation_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    result = build_rebuild_bundles_from_artifacts(
        context,
        pipeline_root=pipeline_root,
        corpus_db_path=tmp_path / "corpus.db",
    )

    assert result["bundle_count"] == 1
    assert result["missing_structured_count"] == 0
    assert result["missing_validation_count"] == 0
    assert result["projection_preview"][0]["projection_id"] == "housing.default.v1"
    bundle = result["bundles"][0]
    assert bundle.normalized_path == normalized_dir / "invoice.pdf.structured.normalized.json"
    assert bundle.structured_path == structured_dir / "invoice.pdf.structured.json"
    assert bundle.validation_path == validation_dir / "invoice.pdf.vision_validation_report.json"


def test_build_rebuild_bundles_from_artifacts_prefers_files_sidecar_for_file_profile(
    tmp_path: Path,
    mixed_structured,
    files_validation_report,
    legacy_validation_report,
    vision_normalized,
):
    context = ModuleContext(tmp_path)
    pipeline_root = tmp_path / "pipeline"
    normalized_dir = pipeline_root / "normalized"
    structured_dir = pipeline_root / "structured"
    validation_dir = pipeline_root / "validation"
    for folder in (normalized_dir, structured_dir, validation_dir):
        folder.mkdir(parents=True)

    (normalized_dir / "kostenplan.xlsx.structured.normalized.json").write_text(
        json.dumps(vision_normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (structured_dir / "kostenplan.xlsx.structured.json").write_text(
        json.dumps(mixed_structured, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (validation_dir / "kostenplan.xlsx.files_validation_report.json").write_text(
        json.dumps(files_validation_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (validation_dir / "kostenplan.xlsx.validation_report.json").write_text(
        json.dumps(legacy_validation_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    result = build_rebuild_bundles_from_artifacts(
        context,
        pipeline_root=pipeline_root,
        corpus_db_path=tmp_path / "corpus.db",
    )

    bundle = result["bundles"][0]
    assert bundle.validation_path == validation_dir / "kostenplan.xlsx.files_validation_report.json"


def test_build_rebuild_bundles_from_artifacts_finds_multiple_nested_artifact_clusters(
    tmp_path: Path,
    vision_structured,
    vision_validation_report,
    vision_normalized,
):
    context = ModuleContext(tmp_path)
    pipelines_root = tmp_path / "pipelines"
    vision_root = pipelines_root / "vision"
    tables_root = pipelines_root / "tables"

    vision_normalized_dir = vision_root / "normalized" / "finance"
    vision_structured_dir = vision_root / "structured" / "finance"
    vision_validation_dir = vision_root / "validation" / "finance"
    for folder in (vision_normalized_dir, vision_structured_dir, vision_validation_dir):
        folder.mkdir(parents=True)

    (vision_normalized_dir / "invoice.pdf.structured.normalized.json").write_text(
        json.dumps(vision_normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (vision_structured_dir / "invoice.pdf.structured.json").write_text(
        json.dumps(vision_structured, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (vision_validation_dir / "invoice.pdf.vision_validation_report.json").write_text(
        json.dumps(vision_validation_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    tables_normalized_dir = tables_root / "normalized"
    tables_normalized_dir.mkdir(parents=True)
    (tables_normalized_dir / "table.pdf.structured.normalized.json").write_text(
        json.dumps(
            {
                "schema_version": "tables-v1",
                "projection": {
                    "projection_id": "tables.default.v1",
                    "master_taxonomy_id": "tables_taxonomy.master",
                    "master_taxonomy_version": "1",
                    "projection_version": "1",
                    "projection_fingerprint": "sha256:tables",
                    "materialization_profile_id": "tables.v1",
                },
                "content": {"rows": []},
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    tables_structured_dir = tables_root / "structured"
    tables_validation_dir = tables_root / "validation"
    tables_structured_dir.mkdir(parents=True)
    tables_validation_dir.mkdir(parents=True)
    (tables_structured_dir / "table.pdf.structured.json").write_text(
        json.dumps(vision_structured, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (tables_validation_dir / "table.pdf.vision_validation_report.json").write_text(
        json.dumps(vision_validation_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    result = build_rebuild_bundles_from_artifacts(
        context,
        pipeline_root=pipelines_root,
        corpus_db_path=tmp_path / "corpus.db",
    )

    assert result["cluster_count"] == 2
    assert result["artifact_roots"] == [str(tables_root), str(vision_root)]
    assert result["bundle_count"] == 2
    normalized_paths = {bundle.normalized_path for bundle in result["bundles"]}
    assert normalized_paths == {
        vision_normalized_dir / "invoice.pdf.structured.normalized.json",
        tables_normalized_dir / "table.pdf.structured.normalized.json",
    }


def test_explicit_sidecar_dirs_fail_fast_when_missing(tmp_path: Path, vision_normalized):
    context = ModuleContext(tmp_path)
    normalized_dir = tmp_path / "normalized"
    normalized_dir.mkdir()
    (normalized_dir / "invoice.pdf.structured.normalized.json").write_text(
        json.dumps(vision_normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Validation-Ordner nicht gefunden"):
        build_rebuild_bundles_from_artifacts(
            context,
            normalized_dir=normalized_dir,
            validation_dir=tmp_path / "missing-validation",
            corpus_db_path=tmp_path / "corpus.db",
        )
