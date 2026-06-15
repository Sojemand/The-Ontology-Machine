"""Path-stable semantic release policy facade."""

from __future__ import annotations

from .shared_identity import build_release_fingerprint
from .policy_analysis import analyze_release, projection_metadata
from .policy_drift import installation_state_drift_reason
from .policy_promotions import (
    _candidate_from_promotion,
    _compact_text,
    _date_value,
    _display_value,
    _normalize_text,
    _numeric_value,
    _promotion_record,
    _promotion_slot_defs,
    _promotion_values,
    _resolve_path_segments,
    _resolve_segments,
    json_dumps,
    materialize_promotions,
)

__all__ = [
    "analyze_release",
    "build_release_fingerprint",
    "installation_state_drift_reason",
    "json_dumps",
    "materialize_promotions",
    "projection_metadata",
]
