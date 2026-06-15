from __future__ import annotations

from pathlib import Path

from orchestrator.pipeline import request_enrichment
from orchestrator.pipeline.request_enrichment_helpers import relative_path_text

from .pipeline_interpreter_input_support import _write_raw


def test_build_working_request_keeps_page_scoped_context_and_single_asset(tmp_path: Path) -> None:
    raw_path = tmp_path / "artifacts" / "raw_extracts" / "story.txt.p002.of004.raw.json"
    request_path = tmp_path / "requests" / "story.txt.p002.of004" / "interpreter.request.json"
    source_path = tmp_path / "source" / "story.txt"
    page_paths = tuple(
        tmp_path / "artifacts" / "page_assets" / "story.hash" / f"page_{page_no:03d}.png"
        for page_no in range(1, 5)
    )
    _write_raw(
        raw_path,
        source={
            "file_name": "story.txt",
            "file_path": "story.txt",
            "content_hash": "sha256:test",
            "page_count": 4,
        },
        context={
            "page_number": 2,
            "document_page_count": 4,
            "source_document_path": "story.txt",
            "page_source_path": "story.txt::page=002-of-004",
        },
        blocks=[
            {"id": "page2_para_0", "type": "paragraph", "value": "Page 2 text", "value_type": "text", "position": {"page": 2}}
        ],
    )

    request = request_enrichment.build_working_request(
        object(),
        module_key="interpreter",
        raw_path=raw_path,
        request_path=request_path,
        working_source_path=source_path,
        working_page_paths=page_paths,
        projection_catalog={"catalog_version": "sha256:test", "master_taxonomy_version": "v1", "projections": []},
    )

    assert request["context"]["page_number"] == 2
    assert request["context"]["document_page_count"] == 4
    assert request["source"]["file_path"] == f"{relative_path_text(source_path, request_path.parent)}::page=002-of-004"
    assert request["context"]["page_source_path"] == "story.txt::page=002-of-004"
    assert len(request["page_assets"]) == 1
    assert request["page_assets"][0]["page"] == 2
    assert Path(request["page_assets"][0]["path"]).name == "page_002.png"
