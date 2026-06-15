from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.pipeline import request_enrichment

from .pipeline_interpreter_input_support import _write_raw


def test_build_working_request_requires_projection_catalog(tmp_path: Path) -> None:
    raw_path = tmp_path / "input.raw.json"
    _write_raw(
        raw_path,
        source={"file_name": "scan.jpg", "file_path": "scan.jpg", "content_hash": "sha256:test", "page_count": 1},
        context={},
        blocks=[{"id": "b1", "type": "paragraph", "value": "hello", "value_type": "text", "position": {"page": 1}}],
    )

    with pytest.raises(ValueError, match="projection_catalog"):
        request_enrichment.build_working_request(
            object(),
            module_key="interpreter",
            raw_path=raw_path,
            request_path=tmp_path / "requests" / "interpreter.request.json",
            working_source_path=tmp_path / "source" / "scan.jpg",
            working_page_paths=(tmp_path / "artifacts" / "page_001.png",),
        )


def test_build_working_request_uses_injected_projection_catalog_without_legacy_runtime_fields(tmp_path: Path) -> None:
    raw_path = tmp_path / "input.raw.json"
    _write_raw(
        raw_path,
        source={"file_name": "scan.jpg", "file_path": "scan.jpg", "content_hash": "sha256:test", "page_count": 1},
        context={},
        blocks=[{"id": "b1", "type": "paragraph", "value": "hello", "value_type": "text", "position": {"page": 1}}],
    )

    request = request_enrichment.build_working_request(
        object(),
        module_key="interpreter",
        raw_path=raw_path,
        request_path=tmp_path / "requests" / "interpreter.request.json",
        working_source_path=tmp_path / "source" / "scan.jpg",
        working_page_paths=(tmp_path / "artifacts" / "page_001.png",),
        projection_catalog={
            "catalog_version": "sha256:runtime",
            "release_id": "semantic_release.default",
            "release_version": "2026-03-28.v6",
            "master_taxonomy_version": "v1",
            "master_taxonomy_id": "vision_taxonomy",
            "master_taxonomy_release_id": "sha256:master-line",
            "release_fingerprint": "sha256:semantic-default",
            "runtime_locale": "en",
            "projections": [],
        },
    )

    assert request["projection_catalog"]["release_id"] == "semantic_release.default"
    assert request["projection_catalog"]["master_taxonomy_release_id"] == "sha256:master-line"
    assert request["projection_catalog"]["runtime_locale"] == "en"
    assert "runtime_trace" not in request
    assert "compression_audit" not in request
