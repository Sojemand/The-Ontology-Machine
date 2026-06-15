from __future__ import annotations

from pathlib import Path

import ingestion_layer_vision.orchestrator_contract as merged_contract
import ingestion_layer_file.orchestrator_contract as file_contract


def test_classify_document_golden_born_digital_pdf(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "invoice.pdf"
    source_path.write_bytes(b"%PDF-1.4\n")
    captured: dict[str, Path] = {}

    def fake_pdf_extract(path: Path) -> dict:
        captured["path"] = path
        return {
            "status": "success",
            "needs_ocr": False,
            "metadata": {
                "page_count": 2,
                "text_block_count": 14,
                "avg_chars_per_page": 840.0,
                "text_density": "dense",
                "has_images": True,
            },
        }

    monkeypatch.setattr(file_contract, "extract_pdf_text", fake_pdf_extract)

    response = file_contract._dispatch({"action": "classify_document", "source_path": str(source_path)})
    public_response = merged_contract._dispatch({"action": "classify_document", "source_path": str(source_path)})

    assert captured["path"] == source_path
    assert response["status"] == "ok"
    assert response["classification"] == "born_digital_pdf"
    assert "text_density=dense" in response["reason"]
    assert "avg_chars_per_page=840.0" in response["reason"]
    assert public_response["status"] == "ok"
    assert public_response["classification"] == "born_digital_pdf"
    assert public_response["optimizer_profile"] == "file"
    assert public_response["routing"] == {
        "contract_module": "ingestion_layer_vision.orchestrator_contract",
        "action": "extract_document",
        "optimizer_profile": "file",
    }


def test_classify_document_golden_scan_pdf_from_ocr_signal(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "scan.pdf"
    source_path.write_bytes(b"%PDF-1.4\n")

    def fake_pdf_extract(_path: Path) -> dict:
        return {
            "status": "success",
            "needs_ocr": True,
            "metadata": {
                "page_count": 1,
                "text_block_count": 0,
                "avg_chars_per_page": 0.0,
            },
        }

    monkeypatch.setattr(file_contract, "extract_pdf_text", fake_pdf_extract)

    response = merged_contract._dispatch(
        {
            "action": "classify_document",
            "optimizer_profile": "vision",
            "source_path": str(source_path),
        }
    )

    assert response["status"] == "ok"
    assert response["classification"] == "scan_pdf"
    assert response["optimizer_profile"] == "vision"
    assert response["source_kind"] == "pdf"
    assert "needs_ocr=true" in response["reason"]


def test_public_classify_document_routes_image_sources_to_vision(tmp_path: Path) -> None:
    source_path = tmp_path / "scan.png"
    source_path.write_bytes(b"not-a-real-image")

    response = merged_contract._dispatch({"action": "classify_document", "source_path": str(source_path)})

    assert response["status"] == "ok"
    assert response["classification"] == "image_document"
    assert response["optimizer_profile"] == "vision"
    assert response["source_kind"] == "image"
    assert response["routing"]["optimizer_profile"] == "vision"


def test_public_classify_document_routes_non_pdf_files_to_file_profile(tmp_path: Path) -> None:
    source_path = tmp_path / "letter.docx"
    source_path.write_bytes(b"not-a-real-docx")

    response = merged_contract._dispatch({"action": "classify_document", "source_path": str(source_path)})

    assert response["status"] == "ok"
    assert response["classification"] == "file_document"
    assert response["optimizer_profile"] == "file"
    assert response["source_kind"] == "file"
    assert response["routing"]["optimizer_profile"] == "file"


def test_classify_document_rejects_non_pdf_sources(tmp_path: Path) -> None:
    source_path = tmp_path / "notes.txt"
    source_path.write_text("plain text", encoding="utf-8")

    response = file_contract._dispatch({"action": "classify_document", "source_path": str(source_path)})

    assert response["status"] == "error"
    assert "classify_document" in response["error"]
    assert "PDF" in response["error"]


def test_classify_document_reports_extractor_errors(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "broken.pdf"
    source_path.write_bytes(b"%PDF-1.4\n")

    def fake_pdf_extract(_path: Path) -> dict:
        return {"status": "error", "errors": ["xref table unreadable"]}

    monkeypatch.setattr(file_contract, "extract_pdf_text", fake_pdf_extract)

    response = file_contract._dispatch({"action": "classify_document", "source_path": str(source_path)})

    assert response == {"status": "error", "error": "xref table unreadable"}
