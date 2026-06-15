from __future__ import annotations

from pathlib import Path

from .sample_projection_catalog import build_sample_projection_catalog

_PNG_PAGE_1 = b"\x89PNG\r\n\x1a\npage-001"
_PNG_PAGE_2 = b"\x89PNG\r\n\x1a\npage-002"


def build_sample_request(tmp_path: Path) -> dict:
    page_dir = tmp_path / "page_assets" / "scan_pdf"
    page1 = _write_page(page_dir / "page_001.png", _PNG_PAGE_1)
    page2 = _write_page(page_dir / "page_002.png", _PNG_PAGE_2)
    return {
        "source": {
            "file_name": "scan.pdf",
            "file_path": str(tmp_path / "scan.pdf"),
            "file_ext": "pdf",
            "content_hash": "sha256:test",
            "page_count": 2,
            "document_type": "rechnung",
            "language": "de",
        },
        "context": {
            "page_number": 1,
            "document_page_count": 2,
            "source_document_path": "scan.pdf",
            "page_source_path": "scan.pdf::page=001-of-002",
        },
        "page_assets": [
            {"page": 1, "path": page1, "media_type": "image/png"},
            {"page": 2, "path": page2, "media_type": "image/png"},
        ],
        "ocr_reference": {
            "blocks": [
                {
                    "id": "page1_para_1",
                    "type": "paragraph",
                    "layout_label": "header",
                    "value": "Beitragsrechnung 2026",
                    "value_type": "text",
                    "position": {"page": 1, "paragraph_index": 0},
                    "confidence": 0.98,
                },
                {
                    "id": "page1_para_2",
                    "type": "paragraph",
                    "value": "Rechnungsnummer RE-2026-001",
                    "value_type": "text",
                    "position": {"page": 1, "paragraph_index": 1},
                    "confidence": 0.97,
                },
                {
                    "id": "page1_table0_r1_c1",
                    "type": "cell",
                    "value": "Jahresbeitrag",
                    "value_type": "text",
                    "position": {"page": 1, "table_index": 0, "row": 1, "col": 1},
                    "confidence": 0.95,
                },
                {
                    "id": "page1_table0_r1_c2",
                    "type": "cell",
                    "value": "120,00 EUR",
                    "value_type": "text",
                    "position": {"page": 1, "table_index": 0, "row": 1, "col": 2},
                    "confidence": 0.95,
                },
            ],
        },
        "projection_catalog": build_sample_projection_catalog(),
    }


def _write_page(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return str(path)
