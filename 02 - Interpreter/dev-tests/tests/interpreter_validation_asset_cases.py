from __future__ import annotations

import pytest

from llm_interpreter.interpreter import _validate_request
from llm_interpreter.models import InterpreterConfig
from llm_interpreter.providers import ProviderError
from .interpreter_validation_support import clone_request, process_request_file, write_request


def test_rejects_non_image_assets(sample_request, tmp_path):
    request = clone_request(sample_request)
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET", encoding="utf-8")
    request["page_assets"][0]["path"] = str(secret)
    request["page_assets"][0]["media_type"] = "text/plain"
    with pytest.raises(ProviderError, match="kein Bild"):
        _validate_request(request)


def test_rejects_spoofed_png_with_non_image_bytes(sample_request, tmp_path):
    request = clone_request(sample_request)
    fake_png = tmp_path / "fake.png"
    fake_png.write_text("TOP SECRET", encoding="utf-8")
    request["page_assets"][0]["path"] = str(fake_png)
    request["page_assets"][0]["media_type"] = "image/png"
    with pytest.raises(ProviderError, match="kein gueltiges Bild"):
        _validate_request(request)


def test_rejects_asset_escape_for_file_backed_requests(sample_request, tmp_path):
    request = clone_request(sample_request)
    escape_page = tmp_path.parent / "escape_page.png"
    escape_page.write_bytes(b"\x89PNG\r\n\x1a\nescape")
    request["page_assets"][0]["path"] = str(escape_page)
    input_file = write_request(tmp_path / "requests" / "escape.request.json", request)

    result = process_request_file(input_file, tmp_path / "output" / "escape.structured.json")

    assert result["status"] == "error"
    assert "ausserhalb der erlaubten Wurzeln" in result["error"]


def test_accepts_orchestrator_request_with_sibling_page_assets(sample_request, sample_llm_output, tmp_path):
    request = clone_request(sample_request)
    artifact_root = tmp_path / "artifacts"
    request_file = artifact_root / "requests" / "scan.pdf" / "interpreter.request.json"
    page_root = artifact_root / "page_assets" / "scan.pdf.12345678"
    source_path = artifact_root / "originals" / "scan.pdf"
    _write_two_page_assets(page_root, source_path)
    request["source"]["file_path"] = "../../originals/scan.pdf"
    request["page_assets"][0]["path"] = "../../page_assets/scan.pdf.12345678/page_001.png"
    request["page_assets"][1]["path"] = "../../page_assets/scan.pdf.12345678/page_002.png"
    write_request(request_file, request)

    result = process_request_file(
        request_file,
        tmp_path / "output" / "scan.pdf.structured.json",
        response_json=sample_llm_output,
    )

    assert result["status"] == "ok"


def test_accepts_orchestrator_working_request_with_artifact_page_assets(sample_request, sample_llm_output, tmp_path):
    request = clone_request(sample_request)
    job_root = tmp_path / "job"
    request_file = job_root / "requests" / "interpreter.request.json"
    page_root = job_root / "artifacts" / "page_assets" / "scan.pdf.12345678"
    source_path = job_root / "source" / "scan.pdf"
    _write_two_page_assets(page_root, source_path)
    request["source"]["file_path"] = "../source/scan.pdf"
    request["page_assets"][0]["path"] = "../artifacts/page_assets/scan.pdf.12345678/page_001.png"
    request["page_assets"][1]["path"] = "../artifacts/page_assets/scan.pdf.12345678/page_002.png"
    write_request(request_file, request)

    result = process_request_file(
        request_file,
        tmp_path / "output" / "scan.pdf.structured.json",
        response_json=sample_llm_output,
    )

    assert result["status"] == "ok"


def test_rejects_asset_when_single_file_exceeds_limit(sample_request_file, sample_llm_output, tmp_path):
    result = process_request_file(
        sample_request_file,
        tmp_path / "output" / "scan.pdf.structured.json",
        config=InterpreterConfig(max_page_asset_bytes=8),
        response_json=sample_llm_output,
    )
    assert result["status"] == "error"
    assert "ueberschreitet das Limit" in result["error"]


def test_rejects_asset_when_total_bytes_exceed_limit(sample_request, sample_llm_output, tmp_path):
    input_file = write_request(tmp_path / "requests" / "total.request.json", sample_request)
    result = process_request_file(
        input_file,
        tmp_path / "output" / "total.structured.json",
        config=InterpreterConfig(max_request_asset_bytes=15),
        response_json=sample_llm_output,
    )
    assert result["status"] == "error"
    assert "Gesamtlimit" in result["error"]


def test_rejects_asset_when_page_count_exceeds_limit(sample_request, tmp_path):
    request = clone_request(sample_request)
    request["page_assets"] = _extra_page_assets(tmp_path)
    request["source"]["page_count"] = len(request["page_assets"])
    input_file = write_request(tmp_path / "requests" / "too-many.request.json", request)
    result = process_request_file(
        input_file,
        tmp_path / "output" / "too-many.structured.json",
        config=InterpreterConfig(max_page_assets=12),
    )
    assert result["status"] == "error"
    assert "Limit von 12 Seiten" in result["error"]


def test_env_root_override_allows_asset_outside_request_scope(sample_request, sample_llm_output, tmp_path):
    allowed_root = tmp_path.parent / "shared-assets"
    allowed_root.mkdir(parents=True, exist_ok=True)
    allowed_page = allowed_root / "page_001.png"
    allowed_page.write_bytes(b"\x89PNG\r\n\x1a\noverride")
    request = clone_request(sample_request)
    request["page_assets"][0]["path"] = str(allowed_page)
    input_file = write_request(tmp_path / "requests" / "override.request.json", request)
    result = process_request_file(
        input_file,
        tmp_path / "output" / "override.structured.json",
        config=InterpreterConfig(page_asset_allowed_roots=(allowed_root,)),
        response_json=sample_llm_output,
    )
    assert result["status"] == "ok"


def _write_two_page_assets(page_root, source_path) -> None:
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"%PDF-1.4")
    page_root.mkdir(parents=True, exist_ok=True)
    (page_root / "page_001.png").write_bytes(b"\x89PNG\r\n\x1a\npage-001")
    (page_root / "page_002.png").write_bytes(b"\x89PNG\r\n\x1a\npage-002")


def _extra_page_assets(tmp_path) -> list[dict]:
    extra_pages = []
    for index in range(1, 14):
        page_path = tmp_path / "pages" / f"page_{index:03d}.png"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(str(index), encoding="ascii"))
        extra_pages.append({"page": index, "path": str(page_path), "media_type": "image/png"})
    return extra_pages
