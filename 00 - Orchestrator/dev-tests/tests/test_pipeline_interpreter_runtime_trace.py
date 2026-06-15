from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.pipeline import request_enrichment


def test_build_working_request_rejects_raw_only_runtime_trace_fields(tmp_path: Path) -> None:
    raw_path = tmp_path / "input.raw.json"
    raw_path.write_text(
        json.dumps(
            {
                "schema_version": "optimizer_raw_v2",
                "optimizer_profile": "vision",
                "source": {"file_name": "scan.jpg", "file_path": "scan.jpg", "content_hash": "sha256:test", "page_count": 1},
                "context": {"page_number": 1, "document_page_count": 1, "source_document_path": "scan.jpg", "page_source_path": "scan.jpg::page=001-of-001"},
                "ocr_reference": {"blocks": [{"id": "page1_para_0", "type": "paragraph", "value": "hello", "value_type": "text", "position": {"page": 1}}]},
                "runtime_trace": {"release_fingerprint": "sha256:semantic-default"},
                "compression_audit": {"mode": "legacy_passthrough"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Legacy optimizer raw fields"):
        request_enrichment.build_working_request(
            object(),
            module_key="interpreter",
            raw_path=raw_path,
            request_path=tmp_path / "requests" / "interpreter.request.json",
            working_source_path=tmp_path / "source" / "scan.jpg",
            working_page_paths=(tmp_path / "artifacts" / "page_001.jpg",),
            projection_catalog={"catalog_version": "sha256:runtime", "master_taxonomy_version": "v1", "projections": []},
        )
