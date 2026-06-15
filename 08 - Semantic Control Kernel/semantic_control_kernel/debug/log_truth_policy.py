from __future__ import annotations

from typing import Any


def canonical_truth_required(
    *,
    receipt_present: bool,
    resume_state_present: bool,
    binding_present: bool,
    debug_evidence_present: bool,
) -> dict[str, Any]:
    if receipt_present and resume_state_present and binding_present:
        return {
            "decision": "allowed",
            "used_debug_evidence": False,
            "reason": "canonical_truth_present",
        }
    return {
        "decision": "blocked",
        "used_debug_evidence": bool(debug_evidence_present),
        "reason": "canonical_truth_missing",
    }
