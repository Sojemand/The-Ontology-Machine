from __future__ import annotations

from pathlib import Path

from orchestrator.pipeline import request_enrichment
from orchestrator.pipeline.request_enrichment_helpers import relative_path_text

from .pipeline_interpreter_input_support import _write_raw


def test_build_working_request_creates_minimal_vision_request_from_raw_v2(tmp_path: Path) -> None:
    raw_path = tmp_path / "artifacts" / "raw_extracts" / "scan.jpg.raw.json"
    request_path = tmp_path / "requests" / "scan.jpg" / "interpreter.request.json"
    source_path = tmp_path / "source" / "scan.jpg"
    page_paths = (
        tmp_path / "artifacts" / "page_assets" / "scan.hash" / "page_001.png",
        tmp_path / "artifacts" / "page_assets" / "scan.hash" / "page_002.png",
    )
    _write_raw(
        raw_path,
        source={
            "file_name": "scan.jpg",
            "file_path": "scan.jpg",
            "content_hash": "sha256:test",
            "page_count": 2,
            "document_type": "receipt",
            "language": "de",
        },
        context={},
        blocks=[
            {"id": "page1_para_0", "type": "paragraph", "value": "Alpha", "value_type": "text", "position": {"page": 1}},
            {"id": "page2_para_0", "type": "paragraph", "value": "Beta", "value_type": "text", "position": {"page": 2}},
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

    assert set(request["ocr_reference"]) == {"blocks"}
    assert [block["value"] for block in request["ocr_reference"]["blocks"]] == ["Alpha", "Beta"]
    assert [asset["page"] for asset in request["page_assets"]] == [1, 2]
    assert all(asset["format"] == "png" for asset in request["page_assets"])
    assert all(asset["color_mode"] == "grayscale" for asset in request["page_assets"])
    assert all(asset["bit_depth"] == 8 for asset in request["page_assets"])
    assert all(asset["dpi_x"] == 150 and asset["dpi_y"] == 150 for asset in request["page_assets"])
    assert all(asset["dpi_unit"] == "inch" for asset in request["page_assets"])
    assert request["source"]["file_path"] == relative_path_text(source_path, request_path.parent)
    assert request["context"]["interpreter_profile"] == "vision"
    assert request["projection_catalog"]["catalog_version"] == "sha256:test"
