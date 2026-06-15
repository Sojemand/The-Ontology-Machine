from __future__ import annotations

from phase5_transition_evaluator_support import state_for_rule
from semantic_control_kernel.domain.state_machine.evaluator import StateMachineEvaluator
from semantic_control_kernel.domain.state_machine.models import EligibilityStatus, TransitionInputRefs
from semantic_control_kernel.domain.state_machine.transition_table import get_transition_rule


def test_confirmation_receipt_must_match_state_target_and_gate() -> None:
    rule = get_transition_rule("reset_database")
    state = state_for_rule(rule)
    receipt = {
        "schema_version": "kernel.confirmation_receipt.v1",
        "confirmation_receipt_id": "cfr_ok",
        "confirmation_request_id": "ok",
        "confirmed_at": "2026-05-05T00:00:00Z",
        "confirmed_state_snapshot_identity": {
            "schema_version": "state.snapshot_identity.v1",
            "state_snapshot_id": state.payload["state_snapshot_id"],
        },
        "confirmed_target_identity": state.payload["active_database"]["target_identity"],
        "explanation_hash": "explain",
        "host_surface_identity": "client_frontend_http_pipeline_session",
        "user_decision": "confirmed",
        "function_or_route": "reset_database",
        "confirmation_gate": rule.confirmation_gate,
    }

    allowed = StateMachineEvaluator().evaluate(
        "reset_database",
        state,
        TransitionInputRefs.for_rule(rule, confirmation_receipts={"ok": receipt}),
        confirmation_ref="ok",
    )
    stale = StateMachineEvaluator().evaluate(
        "reset_database",
        state,
        TransitionInputRefs.for_rule(rule, confirmation_receipts={"bad": {**receipt, "confirmation_gate": "wrong"}}),
        confirmation_ref="bad",
    )

    assert allowed.status == EligibilityStatus.ALLOWED.value
    assert stale.status == EligibilityStatus.BLOCKED.value
    assert stale.blockers[0].blocker_code == "confirmation_stale"


def test_confirmation_receipt_accepts_canonical_contract_fields_and_rejects_stale_request_or_target() -> None:
    rule = get_transition_rule("reset_database")
    state = state_for_rule(rule)
    canonical_receipt = {
        "confirmation_receipt_id": "cfr_1",
        "confirmation_request_id": "cfq_1",
        "confirmed_at": "2026-05-05T00:00:00Z",
        "confirmed_state_snapshot_identity": {
            "schema_version": "state.snapshot_identity.v1",
            "state_snapshot_id": state.payload["state_snapshot_id"],
        },
        "confirmed_target_identity": state.payload["active_database"]["target_identity"],
        "host_surface_identity": "client_frontend_http_pipeline_session",
        "schema_version": "kernel.confirmation_receipt.v1",
        "user_decision": "confirmed",
    }

    allowed = StateMachineEvaluator().evaluate(
        "reset_database",
        state,
        TransitionInputRefs.for_rule(rule, confirmation_receipts={"cfq_1": canonical_receipt}),
        confirmation_ref="cfq_1",
    )
    stale_request = StateMachineEvaluator().evaluate(
        "reset_database",
        state,
        TransitionInputRefs.for_rule(rule, confirmation_receipts={"cfq_1": {**canonical_receipt, "confirmation_request_id": "cfq_other"}}),
        confirmation_ref="cfq_1",
    )
    stale_target = StateMachineEvaluator().evaluate(
        "reset_database",
        state,
        TransitionInputRefs.for_rule(
            rule,
            confirmation_receipts={
                "cfq_1": {
                    **canonical_receipt,
                    "confirmed_target_identity": {**canonical_receipt["confirmed_target_identity"], "target_hash": "tgt_other"},
                }
            },
        ),
        confirmation_ref="cfq_1",
    )

    assert allowed.status == EligibilityStatus.ALLOWED.value
    assert stale_request.status == EligibilityStatus.BLOCKED.value
    assert stale_request.blockers[0].blocker_code == "confirmation_stale"
    assert stale_target.status == EligibilityStatus.BLOCKED.value
    assert stale_target.blockers[0].blocker_code == "confirmation_stale"


def test_confirmation_receipt_rejects_missing_canonical_identity_fields() -> None:
    rule = get_transition_rule("reset_database")
    state = state_for_rule(rule)
    canonical_receipt = {
        "confirmation_receipt_id": "cfr_1",
        "confirmation_request_id": "cfq_1",
        "confirmed_at": "2026-05-05T00:00:00Z",
        "confirmed_state_snapshot_identity": {
            "schema_version": "state.snapshot_identity.v1",
            "state_snapshot_id": state.payload["state_snapshot_id"],
        },
        "confirmed_target_identity": state.payload["active_database"]["target_identity"],
        "explanation_hash": "explain",
        "host_surface_identity": "client_frontend_http_pipeline_session",
        "schema_version": "kernel.confirmation_receipt.v1",
        "user_decision": "confirmed",
    }

    for removed_field in ("confirmation_request_id", "confirmed_state_snapshot_identity", "confirmed_target_identity"):
        stale_payload = dict(canonical_receipt)
        stale_payload.pop(removed_field)
        result = StateMachineEvaluator().evaluate(
            "reset_database",
            state,
            TransitionInputRefs.for_rule(rule, confirmation_receipts={"cfq_1": stale_payload}),
            confirmation_ref="cfq_1",
        )

        assert result.status == EligibilityStatus.BLOCKED.value
        assert result.blockers[0].blocker_code == "confirmation_stale"
