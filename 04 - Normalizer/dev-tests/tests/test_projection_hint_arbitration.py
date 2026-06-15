from __future__ import annotations

import pytest

from normalizer_vision.assets import load_local_profile
from normalizer_vision.projection_routing import resolve_projection
from normalizer_vision.projection_routing.arbitration import select_advisory_projection
from normalizer_vision.projection_routing.config import default_routing_settings
from normalizer_vision.projection_routing.types import ProjectionHint


def test_advisory_hint_accepts_high_confidence_with_verified_signals(tmp_project_root) -> None:
    payload = {
        "context": {
            "projection_hint": {
                "projection_id": "operations.default.v1",
                "confidence": 0.9,
                "reason": "Logistics signals visible.",
                "matched_signals": ["delivery note", "transport order"],
            }
        },
        "classification": {"document_type": "delivery_note", "category": "operations", "subcategory": "logistics"},
        "content": {
            "fields": {"document_number": "BK-20220771"},
            "rows": [{"_row_type": "line_item", "description": "Euro pallets"}],
            "free_text": "Transport order delivery note Euro pallets",
        },
    }

    selection = resolve_projection(
        project_root=tmp_project_root,
        fallback_profile=load_local_profile(tmp_project_root, "housing.default.v1"),
        raw_doc=payload,
        hint_mode="advisory",
    )

    assert selection.profile.projection_id == "operations.default.v1"
    assert selection.mode == "hint_validated"
    assert "confidence_bonus=3" in selection.reason
    assert "verified_hint_signals=2/3 [delivery note, transport order]" in selection.reason


def test_advisory_hint_rejects_when_local_challenger_clears_margin(tmp_project_root) -> None:
    payload = {
        "context": {
            "projection_hint": {
                "projection_id": "finance.default.v1",
                "confidence": 0.9,
                "reason": "Payment topic detected.",
                "matched_signals": ["invoice"],
            }
        },
        "classification": {"document_type": "authority_notice", "category": "legal", "subcategory": "official_notice"},
        "content": {
            "fields": {"authority_name": "Stadt Leipzig", "case_id": "AZ-44", "document_number": "K-77"},
            "rows": [{"_row_type": "line_item", "description": "Arrears from notice amount", "balance": "420.00 EUR"}],
            "free_text": "Authority reminder for payment tracking. Case reference AZ-44, treasury reference K-77, open arrears.",
        },
    }

    selection = resolve_projection(
        project_root=tmp_project_root,
        fallback_profile=load_local_profile(tmp_project_root, "housing.default.v1"),
        raw_doc=payload,
        hint_mode="advisory",
    )

    assert selection.profile.projection_id == "legal.public_admin.default.v1"
    assert selection.mode == "hint_rejected"
    assert "best_challenger=legal.public_admin.default.v1" in selection.reason
    assert "challenger_delta=" in selection.reason


@pytest.mark.parametrize(("confidence", "expected_bonus"), [(0.60, 1), (0.80, 2), (0.90, 3)])
def test_select_advisory_projection_applies_confidence_threshold_bonuses(confidence: float, expected_bonus: int) -> None:
    decision = select_advisory_projection(
        scores={
            "housing.default.v1": (0, []),
            "operations.default.v1": (1, ["text_marker:lieferschein"]),
        },
        fallback_projection_id="housing.default.v1",
        hint=ProjectionHint("operations.default.v1", confidence, "hint", []),
        routing_settings=default_routing_settings(),
    )

    assert decision.projection_id == "operations.default.v1"
    assert decision.mode == "hint_validated"
    assert f"confidence_bonus={expected_bonus}" in decision.reason


def test_select_advisory_projection_caps_verified_signal_bonus() -> None:
    decision = select_advisory_projection(
        scores={
            "housing.default.v1": (0, []),
            "operations.default.v1": (
                1,
                ["text_marker:lieferschein", "text_marker:transportauftrag", "text_marker:logistik", "text_marker:palette"],
            ),
        },
        fallback_projection_id="housing.default.v1",
        hint=ProjectionHint(
            "operations.default.v1",
            0.0,
            "hint",
            ["lieferschein", "transportauftrag", "logistik", "palette"],
        ),
        routing_settings=default_routing_settings(),
    )

    assert decision.projection_id == "operations.default.v1"
    assert "verified_hint_signals=3/3" in decision.reason


def test_advisory_unknown_hint_falls_back_even_when_local_best_exists(tmp_project_root) -> None:
    payload = {
        "context": {
            "projection_hint": {
                "projection_id": "unknown.projection.v1",
                "confidence": 0.88,
                "reason": "Uncertain hint.",
                "matched_signals": ["delivery note"],
            }
        },
        "classification": {"document_type": "delivery_note", "category": "operations", "subcategory": "logistics"},
        "content": {
            "fields": {"document_number": "BK-20220771"},
            "rows": [{"_row_type": "line_item", "description": "Euro pallets"}],
            "free_text": "Transport order delivery note Euro pallets",
        },
    }

    selection = resolve_projection(
        project_root=tmp_project_root,
        fallback_profile=load_local_profile(tmp_project_root, "housing.default.v1"),
        raw_doc=payload,
        hint_mode="advisory",
    )

    assert selection.profile.projection_id == "housing.default.v1"
    assert selection.mode == "hint_rejected"
    assert "unknown" in selection.reason
    assert "fallback=housing.default.v1" in selection.reason


def test_advisory_without_hint_uses_strong_local_candidate(tmp_project_root) -> None:
    payload = {
        "classification": {
            "document_type": "narrative_text",
            "category": "personal",
            "subcategory": "creative_writing",
        },
        "content": {
            "fields": {"author_name": "A. Writer"},
            "rows": [],
            "free_text": "Story chapter summary by the author. Personal reflection and fiction merge into one narrative.",
        },
    }

    selection = resolve_projection(
        project_root=tmp_project_root,
        fallback_profile=load_local_profile(tmp_project_root, "housing.default.v1"),
        raw_doc=payload,
        hint_mode="advisory",
    )

    assert selection.profile.projection_id == "personal.expression.default.v1"
    assert selection.mode == "local_inferred"
    assert "required_min_score=" in selection.reason
    assert "signals=[" in selection.reason


def test_advisory_without_hint_keeps_fallback_when_local_margin_is_too_small(tmp_project_root) -> None:
    payload = {
        "classification": {"document_type": "general_letter", "category": "other", "subcategory": "other"},
        "content": {
            "fields": {
                "phone": "+49 341 555 10",
                "fax": "+49 341 555 11",
                "email": "kontakt@example.org",
                "website": "example.org",
            },
            "rows": [],
            "free_text": "General letter with contact block and website.",
        },
    }

    selection = resolve_projection(
        project_root=tmp_project_root,
        fallback_profile=load_local_profile(tmp_project_root, "housing.default.v1"),
        raw_doc=payload,
        hint_mode="advisory",
    )

    assert selection.profile.projection_id == "housing.default.v1"
    assert selection.mode == "fallback"
    assert "local routing remains below the release threshold" in selection.reason
