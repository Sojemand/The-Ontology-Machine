"""Deterministic repair rules for projection proposal outputs."""

from __future__ import annotations

from typing import Any

from semantic_control_kernel.validation.llm.common import _STATUS_ALIASES


def repair_projection_proposal(payload: dict[str, Any]) -> None:
    proposals = payload.get("projection_proposals")
    if not isinstance(proposals, list):
        return
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        proposal["status"] = _STATUS_ALIASES.get(str(proposal.get("status") or "").strip().lower(), proposal.get("status") or "draft")
        for key, value in list(proposal.items()):
            if key.startswith("include_") and isinstance(value, list) and "other" not in value:
                value.append("other")


__all__ = ["repair_projection_proposal"]
