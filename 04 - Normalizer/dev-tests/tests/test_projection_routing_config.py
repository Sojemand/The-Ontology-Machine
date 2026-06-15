from __future__ import annotations

import pytest

from normalizer_vision.projection_routing.config import default_routing_settings, validate_routing_settings


def test_default_routing_settings_expose_confidence_prior_defaults() -> None:
    assert default_routing_settings() == {
        "field_signal_limit": 4,
        "row_signal_limit": 3,
        "cell_signal_limit": 6,
        "hint_confidence_low_threshold": 0.6,
        "hint_confidence_medium_threshold": 0.8,
        "hint_confidence_high_threshold": 0.9,
        "hint_confidence_low_bonus": 1,
        "hint_confidence_medium_bonus": 2,
        "hint_confidence_high_bonus": 3,
        "matched_signal_bonus_cap": 3,
        "hint_reject_margin": 3,
        "no_hint_local_min_score": 4,
        "no_hint_local_margin": 3,
    }


def test_validate_routing_settings_rejects_legacy_hint_threshold_keys() -> None:
    with pytest.raises(ValueError, match="unbekannte Felder"):
        validate_routing_settings({"min_route_score": 7, "min_hint_score": 4})


def test_validate_routing_settings_rejects_unordered_confidence_thresholds() -> None:
    with pytest.raises(ValueError, match="thresholds"):
        validate_routing_settings(
            {
                "hint_confidence_low_threshold": 0.8,
                "hint_confidence_medium_threshold": 0.7,
                "hint_confidence_high_threshold": 0.9,
            }
        )


def test_validate_routing_settings_rejects_non_positive_margin() -> None:
    with pytest.raises(ValueError, match="hint_reject_margin"):
        validate_routing_settings({"hint_reject_margin": 0})
