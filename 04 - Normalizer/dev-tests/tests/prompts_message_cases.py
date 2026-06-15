from __future__ import annotations

from normalizer_vision.assets import load_local_profile
from normalizer_vision.prompts import build_messages, describe_profile, get_output_schema_text


def test_build_messages_contains_taxonomy_and_input(tmp_project_root, sample_structured_input):
    profile = load_local_profile(tmp_project_root, "housing.default.v1")
    messages = build_messages(sample_structured_input, profile)
    assert len(messages) == 2
    assert "utility_cost_statement" in messages[1]["content"]
    assert "Input structured.json" in messages[1]["content"]
    assert "Use only codes from the active taxonomy profile." in messages[0]["content"]
    assert "not a patch list and not a raw copy" in messages[0]["content"]
    assert "_units is allowed only as a sparse override map" in messages[0]["content"]
    assert "nullable compatibility fields" in messages[0]["content"]
    assert "Apply domain-specific normalization only when the active Semantic Release" in messages[0]["content"]
    assert "do not apply hidden business, finance, housing, legal, narrative, or other domain assumptions" in messages[0]["content"]
    assert "raw_classification" in messages[1]["content"]
    assert "Do not return _source_refs" in messages[1]["content"]
    assert "If processing.needs_review is true, processing.review_reason MUST contain a concrete" in messages[1]["content"]
    assert "Use _units only as a sparse override map" in messages[1]["content"]
    assert "Fill nullable compatibility fields only when supported" in messages[1]["content"]
    assert "Apply domain-specific normalization only when the active Semantic Release" in messages[1]["content"]
    assert "money values in rows should be bare numbers" not in messages[1]["content"]
    assert "prefer account_delta for signed booking movements" not in messages[1]["content"]
    assert "advance-payment adjustments" not in messages[0]["content"]
    assert "If needs_review=true, review_reason MUST contain a concrete, non-empty short reason" in messages[0]["content"]
    assert "context.description is the primary semantic summary for display, FTS, and embeddings" in messages[0]["content"]
    assert "1 to 3 short, information-dense English sentences" in messages[0]["content"]
    assert '"page of", "the page shows", or "Page X of Y"' in messages[0]["content"]
    assert "For narrative_text or creative fragments" in messages[0]["content"]
    assert "For technical, form-like, or regulatory documents" in messages[0]["content"]
    assert '"page of", "the page shows", or "Page X of Y"' in messages[1]["content"]
    assert "visible document role or topic plus 1 to 3 concrete anchors" in messages[1]["content"]
    assert "Promotion materialization contract:" in messages[1]["content"]
    assert "For cardinality=multi, return a JSON array" in messages[1]["content"]


def test_output_schema_text_contains_profile_and_raw_classification():
    text = get_output_schema_text("housing.default.v1")
    assert '"taxonomy_profile_id": "housing.default.v1"' in text
    assert '"raw_classification": {' in text
    assert '"field_code": "value"' in text
    assert '"_row_type": "row_type"' in text
    assert '"cell_code": "compact row value"' in text
    assert '"account_delta": -17.98' not in text
    assert '"_source_refs"' not in text
    assert '"description": "Compact evidence-bound English semantic summary of the document function or topic and its strongest visible anchors."' in text


def test_describe_profile_lists_projection_metadata(tmp_project_root):
    profile = load_local_profile(tmp_project_root, "housing.default.v1")
    text = describe_profile(profile)
    assert "Profile: housing.default.v1" in text
    assert "Label:" in text
    assert "Field codes:" in text
