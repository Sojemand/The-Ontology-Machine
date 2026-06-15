from __future__ import annotations


def build_sample_llm_output() -> dict:
    return {
        "schema_version": "1.0",
        "processing": {
            "interpreter_profile": "vision",
            "model_confidence": 0.91,
            "needs_review": False,
            "review_reason": None,
            "vision_used": True,
        },
        "classification": {
            "document_type": "invoice",
            "document_type_confidence": 0.88,
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
            "plot_number": "17",
        },
        "content": {
            "structure": {
                "type": "form_with_table",
                "columns": ["position", "betrag"],
                "form_fields": ["mitglied"],
            },
            "fields": {
                "document_number": "RE-2026-001",
                "member_name": "Erika Muster",
            },
            "rows": [
                {
                    "position": "Jahresbeitrag",
                    "betrag": 120.0,
                    "_source_refs": {
                        "position": "page1_para_3",
                        "betrag": "page1_para_2",
                    },
                }
            ],
            "segments": [
                {
                    "segment_id": "Page1_Segment1",
                    "unit_kind": "title_line",
                    "page": 1,
                    "sequence": 1,
                    "text": "Beitragsrechnung 2026",
                    "function": "document_heading",
                },
                {
                    "segment_id": "Page1_Segment2",
                    "unit_kind": "key_value_pair",
                    "page": 1,
                    "sequence": 2,
                    "label": "Rechnungsnummer",
                    "text": "Rechnungsnummer RE-2026-001",
                    "function": "document_identifier",
                },
                {
                    "segment_id": "Page1_Segment3",
                    "unit_kind": "list_item",
                    "page": 1,
                    "sequence": 3,
                    "text": "Jahresbeitrag Parzelle 17",
                    "function": "charge_description",
                },
                {
                    "segment_id": "Page1_Segment4",
                    "unit_kind": "summary_block",
                    "page": 1,
                    "sequence": 4,
                    "text": "Gesamtbetrag 120,00 EUR",
                    "function": "amount_due_statement",
                },
                {
                    "segment_id": "Page1_Segment5",
                    "unit_kind": "key_value_pair",
                    "page": 1,
                    "sequence": 5,
                    "label": "Mitglied",
                    "text": "Mitglied Erika Muster",
                    "function": "party_identification",
                },
            ],
            "free_text": (
                "Beitragsrechnung 2026\nRechnungsnummer RE-2026-001\n"
                "Jahresbeitrag Parzelle 17\nGesamtbetrag 120,00 EUR\nMitglied Erika Muster"
            ),
        },
    }
