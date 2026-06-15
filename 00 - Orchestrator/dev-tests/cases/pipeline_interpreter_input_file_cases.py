from __future__ import annotations

from pathlib import Path

from orchestrator.pipeline import request_enrichment

from .pipeline_interpreter_input_support import _write_raw


def test_build_working_request_creates_minimal_file_request_from_raw_v2(tmp_path: Path) -> None:
    raw_path = tmp_path / "artifacts" / "raw_extracts" / "docx.p001.of001.raw.json"
    request_path = tmp_path / "requests" / "docx" / "interpreter.request.json"
    source_path = tmp_path / "source" / "doc.docx"
    page_path = tmp_path / "artifacts" / "page_assets" / "doc.hash" / "page_001.png"
    block = {
        "id": "para_1",
        "type": "paragraph",
        "value": "Native text bleibt exakt erhalten.",
        "value_type": "text",
        "formatting": {"bold": True},
        "position": {"page": 1, "paragraph_index": 0},
    }
    _write_raw(
        raw_path,
        optimizer_profile="file",
        source={"file_name": "doc.docx", "file_path": "doc.docx", "content_hash": "sha256:test", "page_count": 1},
        context={"page_number": 1, "document_page_count": 1},
        blocks=[block],
    )

    request = request_enrichment.build_working_request(
        object(),
        module_key="interpreter",
        raw_path=raw_path,
        request_path=request_path,
        working_source_path=source_path,
        working_page_paths=(page_path,),
        projection_catalog={"catalog_version": "sha256:test", "master_taxonomy_version": "v1", "projections": []},
    )

    assert request["context"]["interpreter_profile"] == "file"
    assert request["ocr_reference"] == {"blocks": [block]}
    assert len(request["page_assets"]) == 1
    assert request["page_assets"][0]["page"] == 1
    assert Path(request["page_assets"][0]["path"]).name == "page_001.png"
    assert request["page_assets"][0]["media_type"] == "image/png"
    assert request["page_assets"][0]["format"] == "png"
    assert request["page_assets"][0]["color_mode"] == "grayscale"
    assert request["page_assets"][0]["bit_depth"] == 8
    assert request["page_assets"][0]["dpi_x"] == 150
    assert request["page_assets"][0]["dpi_y"] == 150
    assert request["page_assets"][0]["dpi_unit"] == "inch"
    assert "summary" not in request["ocr_reference"]
