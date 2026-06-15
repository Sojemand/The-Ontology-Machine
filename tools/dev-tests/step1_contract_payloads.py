from __future__ import annotations

from typing import Any

from step1_contract_paths import SAMPLE_DATA


def build_interpreter_output() -> dict[str, Any]:
    payload = SAMPLE_DATA.build_sample_llm_output()
    payload["context"]["projection_hint"] = {
        "projection_id": "finance.default.v1",
        "confidence": 0.93,
        "reason": "Rechnung, Gesamtbetrag und Mitgliedsbeitrag sprechen fuer Finance.",
        "matched_signals": ["finance", "invoice", "gesamtbetrag"],
    }
    return payload


def build_normalizer_output() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "processing": {
            "model_confidence": 0.92,
            "needs_review": False,
            "review_reason": None,
            "vision_used": False,
        },
        "classification": {
            "document_type": "invoice",
            "document_type_confidence": 0.92,
            "category": "finance",
            "subcategory": "beitragsrechnung",
            "language": "de",
            "is_scan": True,
            "has_handwriting": False,
            "page_count": 2,
        },
        "context": {
            "company": "Kleingartenverein Sonnenschein e.V.",
            "document_date": "2026-03-13",
            "document_title": "Beitragsrechnung 2026",
            "description": "Jahresbeitrag Parzelle 17",
            "tags": ["kleingarten", "beitrag"],
            "people": [],
            "organizations": ["Kleingartenverein Sonnenschein e.V."],
            "locations": ["Berlin"],
            "date_range": {"from": None, "to": None},
            "currencies": ["EUR"],
            "total_monetary_value": 120.0,
            "recipient_primary": "Erika Muster",
            "normalization_notes": [
                "Projection hint was retained for the finance projection baseline case."
            ],
        },
        "content": {
            "structure": {
                "type": "form_with_table",
                "columns": ["position", "betrag"],
                "form_fields": ["recipient_primary", "document_number"],
            },
            "fields": {
                "document_number": "RE-2026-001",
                "recipient_primary": "Erika Muster",
            },
            "rows": [
                {
                    "_row_type": "invoice_line",
                    "position": "Jahresbeitrag",
                    "betrag": 120.0,
                    "_units": {"betrag": "EUR"},
                }
            ],
            "free_text": (
                "Beitragsrechnung 2026 Rechnungsnummer RE-2026-001 Jahresbeitrag "
                "Parzelle 17 Gesamtbetrag 120,00 EUR Mitglied Erika Muster"
            ),
        },
    }
