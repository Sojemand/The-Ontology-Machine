"""Tests for deterministic output enrichment."""
from __future__ import annotations

import copy

from llm_interpreter.interpreter import _enrich_output


def test_fills_processing_and_source(sample_request, sample_llm_output):
    llm_result = copy.deepcopy(sample_llm_output)
    _enrich_output(llm_result, sample_request, provider_name="openai", model="gpt-5.4")
    assert llm_result["processing"]["provider"] == "openai"
    assert llm_result["processing"]["interpreter_profile"] == "vision"
    assert llm_result["processing"]["vision_used"] is True
    assert llm_result["source"]["file_name"] == "scan.pdf"
    assert llm_result["classification"]["page_count"] == 2
    assert llm_result["schema_version"] == "1.0"
    assert "durchschnittlicher_stundensatz" not in llm_result["context"]
    assert llm_result["content"]["free_text"].startswith("Beitragsrechnung 2026")


def test_promotes_missing_context_values_from_fields_and_rows(sample_request, sample_llm_output):
    llm_result = copy.deepcopy(sample_llm_output)
    llm_result["context"] = {
        "company": "Kleingartenverein Sonnenschein e.V.",
        "tags": [],
        "people": [],
        "organizations": [],
        "locations": [],
        "date_range": {"from": None, "to": None},
    }
    llm_result["content"]["fields"] = {
        "invoice_number": {"value": "RE-2026-001"},
        "debit_date": {"value": "2026-04-15"},
        "recipient": {"value": "Erika Muster"},
        "currency": {"value": "eur"},
    }
    llm_result["content"]["rows"] = [
        {"position": "Gesamtkosten", "netto_eur": 100.0, "umsatzsteuer_eur": 19.0, "brutto_eur": 119.0},
        {"position": "zu zahlender Betrag", "brutto_eur": 120.0},
    ]
    _enrich_output(llm_result, sample_request, provider_name="openai", model="gpt-5.4")
    assert llm_result["context"]["document_number"] == "RE-2026-001"
    assert llm_result["context"]["due_date"] == "2026-04-15"
    assert llm_result["context"]["counterparty"] == "Erika Muster"
    assert llm_result["context"]["currencies"] == ["EUR"]
    assert llm_result["context"]["net_amount"] == 100
    assert llm_result["context"]["tax_amount"] == 19
    assert llm_result["context"]["total_monetary_value"] == 120
    assert llm_result["context"]["tax_rate"] == 19


def test_does_not_backfill_context_from_ocr_reference_facts(sample_request, sample_llm_output):
    llm_result = copy.deepcopy(sample_llm_output)
    llm_result["context"] = {
        "company": "Kleingartenverein Sonnenschein e.V.",
        "tags": [],
        "people": [],
        "organizations": [],
        "locations": [],
        "date_range": {"from": None, "to": None},
    }
    llm_result["content"]["fields"] = {}
    llm_result["content"]["rows"] = []

    _enrich_output(llm_result, sample_request, provider_name="openai", model="gpt-5.4")

    assert "document_number" not in llm_result["context"]
    assert "currencies" not in llm_result["context"]


def test_marks_review_when_promoted_amounts_are_inconsistent(sample_request, sample_llm_output):
    llm_result = copy.deepcopy(sample_llm_output)
    llm_result["context"]["total_monetary_value"] = None
    llm_result["context"]["net_amount"] = None
    llm_result["context"]["tax_amount"] = None
    llm_result["content"]["rows"] = [
        {"position": "Gesamtkosten", "netto_eur": 100.0, "umsatzsteuer_eur": 50.0, "brutto_eur": 120.0}
    ]
    _enrich_output(llm_result, sample_request, provider_name="openai", model="gpt-5.4")
    assert llm_result["processing"]["needs_review"] is True
    assert "net + tax weicht > 5% von gross ab" in (llm_result["processing"]["review_reason"] or "")
