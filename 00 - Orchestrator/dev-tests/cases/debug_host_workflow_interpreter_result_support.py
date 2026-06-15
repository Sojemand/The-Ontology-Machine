from __future__ import annotations

import json


def write_optimizer_result(session) -> None:
    raw_path = session.output_root / "raw_extracts" / "docs" / "invoice.raw.json"
    page_path = session.output_root / "page_assets" / "docs" / "invoice" / "page_001.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("{}", encoding="utf-8")
    page_path.write_text("png", encoding="utf-8")
    _write_result(session, {
        "raw_extracts": ["outputs/raw_extracts/docs/invoice.raw.json"],
        "page_assets": ["outputs/page_assets/docs/invoice/page_001.png"],
    })


def write_optimizer_result_with_page_raw(session) -> None:
    doc_raw_path = session.output_root / "raw_extracts" / "docs" / "invoice.raw.json"
    page_raw_path = session.output_root / "raw_extracts" / "invoice.p001.of001.raw.json"
    page_path = session.output_root / "page_assets" / "docs" / "invoice" / "page_001.png"
    doc_raw_path.parent.mkdir(parents=True, exist_ok=True)
    page_raw_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    doc_raw_path.write_text(json.dumps(_file_raw_payload("invoice.pdf", "invoice.pdf")), encoding="utf-8")
    page_raw_path.write_text(json.dumps(_page_raw_payload()), encoding="utf-8")
    page_path.write_text("png", encoding="utf-8")
    _write_result(session, {
        "raw_extracts": [
            "outputs/raw_extracts/docs/invoice.raw.json",
            "outputs/raw_extracts/invoice.p001.of001.raw.json",
        ],
        "page_assets": ["outputs/page_assets/docs/invoice/page_001.png"],
    })


def write_optimizer_result_with_page_assets(session) -> None:
    raw_path = session.output_root / "raw_extracts" / "docs" / "invoice.raw.json"
    page_path = session.output_root / "page_assets" / "docs" / "invoice" / "page_001.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("{}", encoding="utf-8")
    page_path.write_text("png", encoding="utf-8")
    _write_result(session, {
        "raw_extracts": ["outputs/raw_extracts/docs/invoice.raw.json"],
        "page_assets": ["outputs/page_assets/docs/invoice/page_001.png"],
    })


def write_optimizer_result_with_trailing_space_raw(session) -> None:
    raw_path = session.output_root / "raw_extracts" / "Auftrag Fa  HAL .raw.json"
    page_path = session.output_root / "page_assets" / "Auftrag Fa  HAL" / "page_001.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(_legacy_raw_payload()), encoding="utf-8")
    page_path.write_text("png", encoding="utf-8")
    _write_result(session, {
        "raw_extracts": ["outputs/raw_extracts/Auftrag Fa  HAL .raw.json"],
        "page_assets": ["outputs/page_assets/Auftrag Fa  HAL/page_001.png"],
    })


def write_batch_optimizer_result(session) -> None:
    raw_items = []
    page_items = []
    for name in ("a", "b"):
        raw_path = session.output_root / "raw_extracts" / "batch" / f"{name}.raw.json"
        page_path = session.output_root / "page_assets" / "batch" / name / "page_001.png"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text("{}", encoding="utf-8")
        page_path.write_text("png", encoding="utf-8")
        raw_items.append(f"outputs/raw_extracts/batch/{name}.raw.json")
        page_items.append(f"outputs/page_assets/batch/{name}/page_001.png")
    _write_result(session, {"raw_extracts": raw_items, "page_assets": page_items})


def _write_result(session, outputs: dict) -> None:
    session.result_path.write_text(
        json.dumps({"status": "ok", "summary": "optimizer done", "outputs": outputs}),
        encoding="utf-8",
    )


def _file_raw_payload(file_name: str, file_path: str) -> dict:
    return {
        "schema_version": "optimizer_raw_v2",
        "optimizer_profile": "file",
        "source": {"file_name": file_name, "file_path": file_path, "page_count": 1},
        "context": {"source_document_path": file_path, "document_page_count": 1},
        "ocr_reference": {"blocks": []},
    }


def _page_raw_payload() -> dict:
    payload = _file_raw_payload("invoice.pdf", "invoice.pdf")
    payload["context"] = {
        "page_number": 1,
        "source_document_path": "invoice.pdf",
        "page_source_path": "invoice.pdf::page=001-of-001",
        "document_page_count": 1,
    }
    return payload


def _legacy_raw_payload() -> dict:
    return {
        "optimizer_profile": "file",
        "doc": {"file_name": "Auftrag Fa  HAL .msg", "file_path": "Auftrag Fa  HAL .msg", "page_count": 1},
        "ctx": {},
        "pages": [{"page": 1, "blocks": [], "tables": []}],
    }
