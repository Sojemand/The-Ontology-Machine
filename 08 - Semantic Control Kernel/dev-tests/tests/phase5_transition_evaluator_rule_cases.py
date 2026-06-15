from __future__ import annotations

from phase5_transition_evaluator_support import state_for_rule
from semantic_control_kernel.domain.state_machine.evaluator import StateMachineEvaluator
from semantic_control_kernel.domain.state_machine.models import ConfirmationGate, EligibilityStatus, TransitionInputRefs
from semantic_control_kernel.domain.state_machine.transition_table import TRANSITION_RULES, get_transition_rule


def test_evaluator_allows_or_requests_confirmation_for_valid_fixture_per_rule() -> None:
    evaluator = StateMachineEvaluator()

    for rule in TRANSITION_RULES:
        result = evaluator.evaluate(rule.function_or_route, state_for_rule(rule), TransitionInputRefs.for_rule(rule))
        if rule.deprecated:
            assert result.status == EligibilityStatus.DEPRECATED_FORBIDDEN.value
        elif rule.confirmation_gate == ConfirmationGate.NONE.value:
            assert result.status == EligibilityStatus.ALLOWED.value, rule.function_or_route
            assert result.post_state_when_allowed is not None
        else:
            assert result.status == EligibilityStatus.CONFIRMATION_REQUIRED.value, rule.function_or_route
            assert result.required_confirmation_gate == rule.confirmation_gate


def test_evaluator_returns_state_blocker_for_invalid_transition_per_rule() -> None:
    evaluator = StateMachineEvaluator()

    for rule in TRANSITION_RULES:
        state = state_for_rule(rule, invalid=True)
        refs = TransitionInputRefs.for_rule(rule)
        if (
            "internal_context" in rule.required_state
            or "detached_context" in rule.required_state
            or "merge_target_context" in rule.required_state
        ):
            refs = TransitionInputRefs(
                present_inputs=frozenset(rule.required_inputs),
                explicit_blockers=("missing_required_state",),
            )
        result = evaluator.evaluate(rule.function_or_route, state, refs)
        assert result.status in {EligibilityStatus.BLOCKED.value, EligibilityStatus.DEPRECATED_FORBIDDEN.value}
        assert result.blockers
        assert result.blockers[0].to_dict()["schema_version"] == "state.blocker.v1"


def test_removed_update_semantic_release_alias_is_blocked_as_unknown() -> None:
    rule = get_transition_rule("write_semantic_release")
    result = StateMachineEvaluator().evaluate(
        "update_semantic_release",
        state_for_rule(rule),
        TransitionInputRefs(),
    )

    assert result.status == EligibilityStatus.BLOCKED.value
    assert result.blockers[0].blocker_code == "unknown_state"
