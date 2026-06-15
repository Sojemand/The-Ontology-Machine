from __future__ import annotations

import json
from pathlib import Path

from validator_vision.models import report_name


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def file_structured(
    *,
    content_hash: str,
    fields: dict,
    rows: list[dict],
    free_text: str,
    context: dict | None = None,
    segments: list[dict] | None = None,
) -> dict:
    return {
        "schema_version": "1.0",
        "processing": {
            "interpreter_profile": "file",
            "model_confidence": 0.9,
            "needs_review": False,
            "review_reason": None,
            "vision_used": True,
        },
        "classification": {
            "document_type": "invoice",
            "category": "operations",
            "subcategory": "rechnung",
            "language": "de",
            "is_scan": False,
            "has_handwriting": False,
            "page_count": 1,
        },
        "context": context or {},
        "content": {
            "fields": fields,
            "rows": rows,
            "free_text": free_text,
            "segments": segments or [],
        },
        "source": {
            "file_name": "invoice.docx",
            "file_path": "C:/docs/invoice.docx",
            "content_hash": content_hash,
        },
    }


def file_raw(
    *,
    content_hash: str,
    sections: list,
    ctx: dict | None = None,
    facts: dict | None = None,
    tables: list[dict] | None = None,
) -> dict:
    del ctx
    blocks: list[dict] = []
    for index, section in enumerate(sections):
        section_payload = section if isinstance(section, dict) else {"page": 1, "text": section}
        text = str(section_payload.get("text", "") or "").strip()
        if not text:
            continue
        page = int(section_payload.get("page") or 1)
        blocks.append(
            {
                "id": str(section_payload.get("id") or f"page{page}_para_{index}"),
                "type": "paragraph",
                "value": text,
                "value_type": "text",
                "position": {"page": page, "paragraph_index": index},
            }
        )
    for fact_name, fact in (facts or {}).items():
        if not isinstance(fact, dict):
            continue
        value = fact.get("raw_value", fact.get("value"))
        if value in (None, ""):
            continue
        blocks.append(
            {
                "id": f"fact_{fact_name}",
                "type": "paragraph",
                "value": str(value),
                "value_type": "text",
                "position": {"page": 1, "paragraph_index": len(blocks)},
            }
        )
    for table_index, table in enumerate(tables or []):
        if not isinstance(table, dict):
            continue
        page = int(table.get("page") or 1)
        for row_index, row in enumerate(table.get("rows", []) or []):
            if not isinstance(row, list):
                continue
            for col_index, cell in enumerate(row):
                if cell in (None, ""):
                    continue
                blocks.append(
                    {
                        "id": f"page{page}_table{table_index}_r{row_index}_c{col_index}",
                        "type": "cell",
                        "value": str(cell),
                        "value_type": "text",
                        "position": {
                            "page": page,
                            "table_index": table_index,
                            "row": row_index,
                            "col": col_index,
                        },
                    }
                )
    return {
        "schema_version": "optimizer_raw_v2",
        "optimizer_profile": "file",
        "source": {
            "file_name": "invoice.docx",
            "file_path": "C:/docs/invoice.docx",
            "content_hash": content_hash,
            "page_count": 1,
        },
        "extraction": {"plugin_name": "docx-python", "plugin_version": "1.0.0", "processing_time_ms": 1},
        "metadata": {},
        "context": {},
        "ocr_reference": {"blocks": blocks},
    }


def report_path(report_root: Path, structured_path: Path) -> Path:
    return report_root / report_name(structured_path, "file")
