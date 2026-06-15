from __future__ import annotations

import json

import pytest


@pytest.fixture()
def sample_structured_input() -> dict:
    return {
        "schema_version": "1.0",
        "processing": {
            "model_confidence": 0.77,
            "needs_review": False,
            "review_reason": None,
            "vision_used": True,
            "processed_at": "2026-03-23T09:00:00Z",
            "model": "gpt-5.4",
            "provider": "openai",
        },
        "classification": {
            "document_type": "report",
            "document_type_confidence": 0.63,
            "category": "finance",
            "subcategory": "Betriebskostenabrechnung",
            "language": "de",
            "is_scan": True,
            "has_handwriting": False,
            "page_count": 1,
        },
        "context": {
            "company": "ista",
            "document_date": "2022-04-25",
            "document_title": "Einzelabrechnung Energie- und Betriebskosten - Ihre Daten",
            "description": "Einzelabrechnung fuer Heizung und Warmwasser fuer 2021.",
            "tags": ["heizung", "warmwasser"],
            "people": ["Norman Weiss"],
            "organizations": ["Wohnungsgenossenschaft Grimma eG", "ista"],
            "locations": ["Bonhoefferstr. 15, 04668 Grimma"],
            "date_range": {"from": "2021-01-01", "to": "2021-12-31"},
            "currencies": ["EUR"],
            "total_monetary_value": 596.77,
        },
        "content": {
            "structure": {"type": "form_with_table", "columns": ["beschreibung", "betrag"], "form_fields": ["empfaenger"]},
            "fields": {"document_number": "2702001810", "recipient_name": "Norman Weiss"},
            "rows": [{"_row_type": "history_table", "description": "Heizkosten 2021", "amount": "596,77 EUR", "_source_refs": {"description": "page1_para_3"}}],
            "free_text": "ista Einzelabrechnung Energie- und Betriebskosten 2021 Norman Weiss Heizkosten 596,77 EUR",
        },
    }


@pytest.fixture()
def sample_model_output() -> dict:
    return {
        "schema_version": "1.0",
        "processing": {"model_confidence": 0.86, "needs_review": False, "review_reason": None, "vision_used": False},
        "classification": {
            "document_type": "utility_cost_statement",
            "document_type_confidence": 0.86,
            "category": "finance",
            "subcategory": "utilities",
            "language": "de",
            "is_scan": True,
            "has_handwriting": False,
            "page_count": 1,
        },
        "context": {
            "company": "ista",
            "document_date": "2022-04-25",
            "document_title": "Einzelabrechnung Energie- und Betriebskosten - Ihre Daten",
            "description": "Einzelabrechnung und Kostenanalyse fuer Heizung und Warmwasser fuer den Zeitraum 2021.",
            "tags": ["betriebskostenabrechnung", "heizung", "warmwasser", "ista"],
            "people": ["Norman Weiss"],
            "organizations": ["Wohnungsgenossenschaft Grimma eG", "ista"],
            "locations": ["Bonhoefferstr. 15, 04668 Grimma"],
            "date_range": {"from": "2021-01-01", "to": "2021-12-31"},
            "currencies": ["EUR"],
            "total_monetary_value": 596.77,
            "recipient_primary": "Norman Weiss",
            "property_address": "Bonhoefferstr. 15, 04668 Grimma",
            "normalization_notes": ["Raw document_type was too generic for retrieval."],
        },
        "content": {
            "structure": {
                "type": "form_with_table",
                "columns": ["building_total_heating_cost", "tenant_share_heating_cost"],
                "form_fields": ["issuer", "recipient_primary", "property_address", "property_manager_internal_id", "document_date", "period_from", "period_to"],
            },
            "fields": {
                "issuer": "ista",
                "recipient_primary": "Norman Weiss",
                "property_address": "Bonhoefferstr. 15, 04668 Grimma",
                "property_manager_internal_id": "2702001810",
                "document_date": "2022-04-25",
                "period_from": "2021-01-01",
                "period_to": "2021-12-31",
                "_source_refs": {"property_manager_internal_id": "page1_para_3"},
            },
            "rows": [{
                "_row_type": "cost_breakdown_history",
                "description": "Heizkosten 2021",
                "building_total_heating_cost": 55205.35,
                "tenant_share_heating_cost": 596.77,
                "_units": {"building_total_heating_cost": "EUR", "tenant_share_heating_cost": "EUR"},
                "_source_refs": {"building_total_heating_cost": "page1_para_3", "tenant_share_heating_cost": "page1_para_3"},
            }],
            "free_text": "utility_cost_statement issuer: ista recipient: Norman Weiss document_date: 25.04.2022 period: 01.01.2021-31.12.2021 currency: EUR",
        },
    }


class MockProvider:
    def __init__(self, response_json: dict | None = None):
        self.response_json = response_json or {}
        self.calls = []

    def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
        self.calls.append(
            {
                "messages": messages,
                "schema": schema,
                "max_output_tokens": max_output_tokens,
                "thinking_effort": thinking_effort,
            }
        )
        return json.dumps(self.response_json)

    def is_available(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "mock"


@pytest.fixture()
def mock_provider(sample_model_output) -> MockProvider:
    return MockProvider(sample_model_output)
