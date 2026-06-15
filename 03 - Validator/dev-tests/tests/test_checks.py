from __future__ import annotations

from validator_vision.models import MatchConfig, StructuredDocument
from validator_vision.validator.vision import (
    __all__ as vision_surface_exports,
    check_content_fields,
    check_context_scalars,
    check_free_text_presence,
    check_rows,
    match_date,
    match_number,
    match_string,
    matches_free_text,
)


def _document(**overrides):
    data = {
        "processing": {"interpreter_profile": "vision"},
        "context": {},
        "content": {"free_text": "Invoice 15.03.2024 Amount 318,79 Item Alpha", "fields": {}, "rows": []},
        "source": {},
    }
    data.update(overrides)
    return StructuredDocument.from_dict(data)


def prepared_free_text(text: str):
    return StructuredDocument.from_dict(
        {
            "processing": {"interpreter_profile": "vision"},
            "content": {"free_text": text},
        }
    ).free_text


def test_match_helpers_use_prepared_text():
    cfg = MatchConfig()
    free_text = _document().free_text
    assert match_number(318.79, free_text, 0.01) is True
    assert match_number(0, prepared_free_text("Amount 100"), 0.01) is False
    assert match_date("2024-03-15", free_text) is True
    assert match_string("Item Alpha", free_text, cfg) is True
    assert match_string("INV-15", _document(content={"free_text": "Invoice INV 15", "fields": {}, "rows": []}).free_text, cfg)


def test_vision_surface_exports_stable_contract():
    assert "check_rows" in vision_surface_exports
    assert "normalize_text" in vision_surface_exports
    assert "_parse_numeric_token" in vision_surface_exports


def test_free_text_presence_rejects_non_string_values():
    cfg = MatchConfig(require_free_text=True)
    result = check_free_text_presence(
        StructuredDocument.from_dict(
            {
                "processing": {"interpreter_profile": "vision"},
                "content": {"free_text": ["a", "b"]},
            }
        ),
        cfg,
    )
    assert result.status == "FAIL"
    assert result.issues[0].field == "content.free_text"


def test_context_and_content_checks_operate_on_boundary_document():
    doc = StructuredDocument.from_dict(
        {
            "processing": {"interpreter_profile": "vision"},
            "context": {"company": "Acme GmbH"},
            "content": {
                "free_text": "Acme GmbH Rechnungsnummer RG-2024-15",
                "fields": {"invoice_number": "RG-2024-15"},
            },
        }
    )
    cfg = MatchConfig(context_fields=["company"])
    assert check_context_scalars(doc, cfg).status == "PASS"
    assert check_content_fields(doc, cfg).status == "PASS"


def test_match_number_respects_tolerance_boundary():
    assert match_number(100.0, prepared_free_text("Amount 100,01"), 0.01) is True
    assert match_number(100.0, prepared_free_text("Amount 100,02"), 0.01) is False


def test_match_string_uses_compact_form_only_above_threshold():
    assert match_string("INV-15", prepared_free_text("Invoice INV15"), MatchConfig(min_compact_length=5))
    assert not match_string("INV-15", prepared_free_text("Invoice INV15"), MatchConfig(min_compact_length=6))


def test_match_date_accepts_multiple_serializations():
    free_text = prepared_free_text("Datum 15/03/2024 und 15-03-2024")
    assert match_date("2024-03-15", free_text) is True


def test_matches_free_text_handles_boolean_values():
    cfg = MatchConfig()
    assert matches_free_text(False, prepared_free_text("Status false"), cfg) is True
    assert matches_free_text(True, prepared_free_text("Status false"), cfg) is False


def test_rows_check_keeps_original_indexes():
    doc = StructuredDocument.from_dict(
        {
            "processing": {"interpreter_profile": "vision"},
            "content": {
                "free_text": "Second Item 19,99",
                "rows": [None, {"position": "Second Item", "amount": 19.99}],
            },
        }
    )
    result = check_rows(doc, MatchConfig())
    assert result.status == "PASS"
    assert result.checked == 2


def test_missing_values_create_fail_and_warn_levels():
    doc = StructuredDocument.from_dict(
        {
            "processing": {"interpreter_profile": "vision"},
            "context": {"company": "Missing Company"},
            "content": {"free_text": "Other text", "rows": [{"position": "Missing Row"}]},
        }
    )
    cfg = MatchConfig(context_fields=["company"], scalar_level="FAIL", row_level="WARN")
    assert check_context_scalars(doc, cfg).status == "FAIL"
    assert check_rows(doc, cfg).status == "WARN"


def test_rows_check_uses_next_anchor_when_prior_anchor_missing():
    doc = StructuredDocument.from_dict(
        {
            "processing": {"interpreter_profile": "vision"},
            "content": {
                "free_text": "Description Alpha 19,99",
                "rows": [{"position": "", "description": "Alpha", "amount": 19.99}],
            },
        }
    )

    result = check_rows(doc, MatchConfig())

    assert result.status == "PASS"
    assert result.checked == 2


def test_rows_check_uses_question_anchor_and_skips_page_metadata():
    doc = StructuredDocument.from_dict(
        {
            "processing": {"interpreter_profile": "vision"},
            "content": {
                "free_text": "Welche Bearbeitungstoleranzen werden gefordert?",
                "rows": [{"question": "Welche Bearbeitungstoleranzen werden gefordert?", "page": 5}],
            },
        }
    )

    result = check_rows(doc, MatchConfig())

    assert result.status == "PASS"
    assert result.checked == 1


def test_content_fields_skip_private_and_configured_fields():
    doc = StructuredDocument.from_dict(
        {
            "processing": {"interpreter_profile": "vision"},
            "content": {
                "free_text": "Visible Value",
                "fields": {
                    "_hidden": "Missing Hidden",
                    "ignore_me": "Missing Ignore",
                    "visible": "Visible Value",
                },
            },
        }
    )

    result = check_content_fields(doc, MatchConfig(skip_content_fields=["_source_refs", "ignore_me"]))

    assert result.status == "PASS"
    assert result.checked == 1
