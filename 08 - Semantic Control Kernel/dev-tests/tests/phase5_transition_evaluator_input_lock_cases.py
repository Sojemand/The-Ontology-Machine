from __future__ import annotations

from phase5_transition_evaluator_support import state_for_rule
from semantic_control_kernel.domain.state_machine.evaluator import StateMachineEvaluator
from semantic_control_kernel.domain.state_machine.models import EligibilityStatus, TransitionInputRefs
from semantic_control_kernel.domain.state_machine.transition_table import get_transition_rule


def test_required_inputs_must_be_explicitly_present() -> None:
    rule = get_transition_rule("create_empty_database")
    state = state_for_rule(rule)

    result = StateMachineEvaluator().evaluate("create_empty_database", state, TransitionInputRefs())
    result_from_mapping = StateMachineEvaluator().evaluate("create_empty_database", state, {})

    assert result.status == EligibilityStatus.BLOCKED.value
    assert result.blockers[0].blocker_code == "input_missing"
    assert result_from_mapping.status == EligibilityStatus.BLOCKED.value
    assert result_from_mapping.blockers[0].blocker_code == "input_missing"


def test_active_and_expired_locks_block_mutation_before_state_specific_checks() -> None:
    rule = get_transition_rule("activate_semantic_release")
    state = state_for_rule(rule, active_lock_status="active")

    result = StateMachineEvaluator().evaluate("activate_semantic_release", state, TransitionInputRefs.for_rule(rule))

    assert result.status == EligibilityStatus.BLOCKED.value
    assert result.blockers[0].blocker_code == "active_run_lock_conflict"
