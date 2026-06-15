from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from orchestrator.models import ArtifactPaths
from orchestrator.pipeline import (
    artifact_repository,
    bundle_repository,
    bundle_repository_helpers,
    corpus_workflow,
    request_enrichment,
    success_repository,
    success_repository_steps,
)
from orchestrator.pipeline.request_enrichment_helpers import relative_path_text


def test_table_raws_do_not_publish_extra_page_images(tmp_path: Path) -> None:
    raw_path, primary_path = _write_table_raw(tmp_path)
    record = SimpleNamespace(
        artifacts=SimpleNamespace(
            optimizer_raw_paths=[str(raw_path)],
            optimizer_page_image_paths=[str(primary_path)],
        )
    )

    assert success_repository._extra_request_page_images(record) == []
    assert bundle_repository._extra_request_page_images(record) == []


def test_cleanup_normal_outputs_removes_primary_render_and_raw(tmp_path: Path) -> None:
    raw_path, primary_path = _write_table_raw(tmp_path)
    artifacts = ArtifactPaths(
        optimizer_raw_paths=[str(raw_path)],
        optimizer_page_image_paths=[str(primary_path)],
    )
    record = SimpleNamespace(artifacts=artifacts)

    artifact_repository.cleanup_normal_outputs(SimpleNamespace(), record, allowed_roots=(tmp_path.resolve(),))

    assert not raw_path.exists()
    assert not primary_path.exists()
    assert record.artifacts.optimizer_raw_paths == []
    assert record.artifacts.optimizer_page_image_paths == []


def test_success_page_assets_are_published(tmp_path: Path) -> None:
    raw_path, primary_path = _write_table_raw(tmp_path)
    record = SimpleNamespace(
        relative_path="sheet.xlsx",
        file_name="sheet.xlsx",
        source_path=str(tmp_path / "input" / "sheet.xlsx"),
        original_source_path=str(tmp_path / "input" / "sheet.xlsx"),
        content_hash="sha256:abcdef1234567890",
        artifacts=SimpleNamespace(
            optimizer_raw_paths=[str(raw_path)],
            optimizer_page_image_paths=[str(primary_path)],
        )
    )

    published = success_repository_steps.publish_page_images(
        SimpleNamespace(),
        record,
        tmp_path / "Documents",
        (tmp_path.resolve(),),
        [],
    )

    assert not isinstance(published, str)
    target = tmp_path / "Documents" / "page_images" / "sheet.xlsx.abcdef12" / primary_path.name
    assert published.primary_paths == [target]
    assert published.asset_target_map == {primary_path: target}
    assert target.read_text(encoding="utf-8") == "primary"


def test_error_bundle_does_not_copy_working_page_assets(tmp_path: Path) -> None:
    raw_path, primary_path = _write_table_raw(tmp_path)
    record = SimpleNamespace(
        artifacts=SimpleNamespace(
            optimizer_raw_paths=[str(raw_path)],
            optimizer_page_image_paths=[str(primary_path)],
        )
    )

    copied = bundle_repository_helpers.copy_page_images(
        SimpleNamespace(),
        record,
        tmp_path / "Error Cases",
        allowed_roots=(tmp_path.resolve(),),
    )

    assert copied.primary_paths == ()
    assert copied.page_target_map == {}
    assert list((tmp_path / "Error Cases").rglob("*")) == []


def test_corpus_stage_uses_working_page_asset_dir(tmp_path: Path) -> None:
    page_path = tmp_path / "runtime" / "page_assets" / "scan.hash" / "page_001.png"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text("image", encoding="utf-8")
    record = SimpleNamespace(
        optimizer_profile="vision",
        artifacts=SimpleNamespace(optimizer_page_image_paths=[str(page_path)]),
    )

    assert corpus_workflow._common_page_images_dir(record) == page_path.parent


def test_published_request_drops_unpublished_working_page_asset_paths(tmp_path: Path) -> None:
    source_request_path = tmp_path / "runtime" / "requests" / "scan" / "interpreter.request.json"
    target_request_path = tmp_path / "Documents" / "requests" / "scan" / "interpreter.request.json"
    working_source_path = tmp_path / "runtime" / "source" / "scan.pdf"
    working_page_path = tmp_path / "runtime" / "page_assets" / "scan.hash" / "page_001.png"
    source_request_path.parent.mkdir(parents=True, exist_ok=True)
    working_page_path.parent.mkdir(parents=True, exist_ok=True)
    working_source_path.parent.mkdir(parents=True, exist_ok=True)
    working_page_path.write_text("image", encoding="utf-8")
    working_source_path.write_text("source", encoding="utf-8")
    source_request_path.write_text(
        json.dumps(
            {
                "source": {"file_name": "scan.pdf", "file_path": str(working_source_path)},
                "page_assets": [{"page": 1, "path": str(working_page_path), "media_type": "image/png"}],
                "ocr_reference": {"blocks": []},
            }
        ),
        encoding="utf-8",
    )
    published_source_path = tmp_path / "Documents" / "originals" / "scan.pdf"

    error = request_enrichment.publish_request_copy(
        SimpleNamespace(),
        source_request_path,
        target_request_path,
        allowed_roots=(tmp_path.resolve(),),
        action="Request-Publikation",
        noun="Interpreter-Request",
        source_target=published_source_path,
        page_targets=(),
        page_target_map={},
    )

    assert error == ""
    payload = json.loads(target_request_path.read_text(encoding="utf-8"))
    assert payload["source"]["file_path"] == relative_path_text(published_source_path, target_request_path.parent)
    assert "path" not in payload["page_assets"][0]


def _write_table_raw(tmp_path: Path) -> tuple[Path, Path]:
    raw_path = tmp_path / "raw_extracts" / "sheet.raw.json"
    page_root = tmp_path / "page_images" / "sheet.hash"
    primary_path = page_root / "sheet_001.semantic.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    page_root.mkdir(parents=True, exist_ok=True)
    primary_path.write_text("primary", encoding="utf-8")
    raw_path.write_text(
        json.dumps(
            {
                "renders": {
                    "primary": {"path": str(primary_path), "kind": "semantic_render", "media_type": "image/png"},
                }
            }
        ),
        encoding="utf-8",
    )
    return raw_path, primary_path
