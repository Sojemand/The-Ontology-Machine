from __future__ import annotations

from normalizer_vision.models import load_config


def operations_config(tmp_project_root):
    config = load_config(tmp_project_root)
    config.taxonomy_profile_id = "operations.default.v1"
    config.projection_hint_mode = "off"
    return config


def operations_output(
    *,
    document_type,
    category,
    subcategory,
    document_title,
    description,
    fields,
    rows,
    document_date="2026-01-15",
    company="Wissel & Wiesner GmbH",
    tags=None,
):
    return {
        "schema_version": "1.0",
        "processing": {"model_confidence": 0.91, "needs_review": False, "review_reason": None, "vision_used": False},
        "classification": {
            "document_type": document_type,
            "document_type_confidence": 0.91,
            "category": category,
            "subcategory": subcategory,
            "language": "de",
            "is_scan": False,
            "has_handwriting": False,
            "page_count": 1,
        },
        "context": {
            "company": company,
            "document_date": document_date,
            "document_title": document_title,
            "description": description,
            "tags": list(tags or []),
            "people": [],
            "organizations": [company],
            "locations": [],
            "date_range": {"from": None, "to": None},
            "currencies": [],
            "total_monetary_value": None,
            "normalization_notes": [],
        },
        "content": {"structure": {"type": "mixed", "columns": [], "form_fields": []}, "fields": fields, "rows": rows, "free_text": f"{document_type} {category} {subcategory} {document_title}"},
    }


def apply_operations_raw_signals(payload):
    payload["classification"] = {
        "document_type": "delivery_note",
        "document_type_confidence": 0.93,
        "category": "operations",
        "subcategory": "logistics",
        "language": "de",
        "is_scan": False,
        "has_handwriting": False,
        "page_count": 1,
    }
    payload["content"]["fields"] = {"transportauftrag_nummer": "BK-20220771 - Hin"}
    payload["content"]["rows"] = [{"_row_type": "line_item", "position": 1, "menge": "4", "bezeichnung": "Europaletten"}]
    payload["content"]["free_text"] = "delivery_note operations logistics Transportauftrag Lieferschein Europaletten"
    return payload
