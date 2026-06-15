from __future__ import annotations

from typing import Iterable, Mapping

from semantic_control_kernel.domain.state_machine.models import BlockerSeverity, StateBlocker
from semantic_control_kernel.domain.state_machine.recovery_mapping import BLOCKER_CODES, recovery_for_blocker


LOCK_BLOCKER_CODES = ("expired_lock_requires_recovery", "active_run_lock_conflict")


def make_state_blocker(
    *,
    blocker_code: str,
    function_or_route: str,
    required_state: str,
    actual_state: str,
    target_identity: Mapping[str, object],
    state_snapshot_id: str,
    evidence_refs: Iterable[str] = (),
    technical_detail: str = "",
    severity: str = BlockerSeverity.RECOVERABLE_ERROR.value,
) -> StateBlocker:
    if blocker_code not in BLOCKER_CODES:
        raise ValueError(f"Unknown blocker code: {blocker_code}")
    summary = _summary_for(blocker_code, function_or_route)
    return StateBlocker(
        blocker_code=blocker_code,
        function_or_route=function_or_route,
        recovery_state_class=recovery_for_blocker(blocker_code),
        severity=severity,
        required_state=required_state,
        actual_state=actual_state,
        target_identity=dict(target_identity),
        state_snapshot_id=state_snapshot_id,
        evidence_refs=tuple(str(item) for item in evidence_refs),
        user_visible_summary=summary,
        technical_detail=technical_detail or summary,
    )


def blocker_from_payload(payload: Mapping[str, object]) -> StateBlocker:
    return StateBlocker.from_dict(payload)


def _summary_for(blocker_code: str, function_or_route: str) -> str:
    route = function_or_route or "requested transition"
    return f"{route} blocked by {blocker_code}."
