"""Dependency-free projection routing settings validation."""
from __future__ import annotations

from typing import Any

FIELD_SIGNAL_LIMIT = 4
ROW_SIGNAL_LIMIT = 3
CELL_SIGNAL_LIMIT = 6
HINT_CONFIDENCE_LOW_THRESHOLD = 0.60
HINT_CONFIDENCE_MEDIUM_THRESHOLD = 0.80
HINT_CONFIDENCE_HIGH_THRESHOLD = 0.90
HINT_CONFIDENCE_LOW_BONUS = 1
HINT_CONFIDENCE_MEDIUM_BONUS = 2
HINT_CONFIDENCE_HIGH_BONUS = 3
MATCHED_SIGNAL_BONUS_CAP = 3
HINT_REJECT_MARGIN = 3
NO_HINT_LOCAL_MIN_SCORE = 4
NO_HINT_LOCAL_MARGIN = 3

_THRESHOLD_KEYS = (
    "hint_confidence_low_threshold",
    "hint_confidence_medium_threshold",
    "hint_confidence_high_threshold",
)


def default_routing_settings() -> dict[str, int | float]:
    return {
        "field_signal_limit": FIELD_SIGNAL_LIMIT,
        "row_signal_limit": ROW_SIGNAL_LIMIT,
        "cell_signal_limit": CELL_SIGNAL_LIMIT,
        "hint_confidence_low_threshold": HINT_CONFIDENCE_LOW_THRESHOLD,
        "hint_confidence_medium_threshold": HINT_CONFIDENCE_MEDIUM_THRESHOLD,
        "hint_confidence_high_threshold": HINT_CONFIDENCE_HIGH_THRESHOLD,
        "hint_confidence_low_bonus": HINT_CONFIDENCE_LOW_BONUS,
        "hint_confidence_medium_bonus": HINT_CONFIDENCE_MEDIUM_BONUS,
        "hint_confidence_high_bonus": HINT_CONFIDENCE_HIGH_BONUS,
        "matched_signal_bonus_cap": MATCHED_SIGNAL_BONUS_CAP,
        "hint_reject_margin": HINT_REJECT_MARGIN,
        "no_hint_local_min_score": NO_HINT_LOCAL_MIN_SCORE,
        "no_hint_local_margin": NO_HINT_LOCAL_MARGIN,
    }


def validate_routing_settings(payload: Any) -> dict[str, int | float]:
    defaults = default_routing_settings()
    if payload in (None, ""):
        return defaults
    if not isinstance(payload, dict):
        raise ValueError("projection_routing muss ein Objekt sein.")
    unknown = sorted(set(payload) - set(defaults))
    if unknown:
        raise ValueError(f"projection_routing enthaelt unbekannte Felder: {', '.join(unknown)}")
    normalized: dict[str, int | float] = {}
    for key, default in defaults.items():
        value = payload.get(key, default)
        if key in _THRESHOLD_KEYS:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0 or value > 1:
                raise ValueError(f"projection_routing.{key} muss eine Zahl im Bereich (0, 1] sein.")
            normalized[key] = float(value)
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"projection_routing.{key} muss eine positive Ganzzahl sein.")
        normalized[key] = value
    if not (
        normalized["hint_confidence_low_threshold"]
        < normalized["hint_confidence_medium_threshold"]
        < normalized["hint_confidence_high_threshold"]
    ):
        raise ValueError("projection_routing confidence thresholds muessen strikt aufsteigend sein.")
    return normalized


__all__ = ["default_routing_settings", "validate_routing_settings"]
