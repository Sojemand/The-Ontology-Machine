from __future__ import annotations

from semantic_control_kernel.domain.state_machine.recovery_mapping import BLOCKER_CODES, RECOVERY_BY_BLOCKER
from semantic_control_kernel.domain.state_machine.transition_table import TRANSITION_RULES
from semantic_control_kernel.types.enums import RecoveryStateClass


class StateMachineValidationError(ValueError):
    pass


def validate_transition_table() -> None:
    if len(TRANSITION_RULES) != 30:
        raise StateMachineValidationError(f"Expected 30 transition rules, found {len(TRANSITION_RULES)}.")
    rule_ids = [rule.rule_id for rule in TRANSITION_RULES]
    if len(rule_ids) != len(set(rule_ids)):
        raise StateMachineValidationError("Duplicate transition rule_id found.")
    names = [rule.function_or_route for rule in TRANSITION_RULES]
    if len(names) != len(set(names)):
        raise StateMachineValidationError("Duplicate transition function_or_route found.")
    unknown_blockers = sorted({code for rule in TRANSITION_RULES for code in rule.blocks_if} - set(BLOCKER_CODES))
    if unknown_blockers:
        raise StateMachineValidationError(f"Unknown transition blocker code(s): {', '.join(unknown_blockers)}")
    unknown_recoveries = sorted(
        {state for rule in TRANSITION_RULES for state in rule.default_recovery_states} - set(RecoveryStateClass.values())
    )
    if unknown_recoveries:
        raise StateMachineValidationError(f"Unknown transition recovery state(s): {', '.join(unknown_recoveries)}")


def validate_blocker_recovery_mapping() -> None:
    missing = sorted(set(BLOCKER_CODES) - set(RECOVERY_BY_BLOCKER))
    if missing:
        raise StateMachineValidationError(f"Missing recovery mapping for blocker(s): {', '.join(missing)}")
    recovery_values = set(RecoveryStateClass.values())
    unknown = sorted(set(RECOVERY_BY_BLOCKER.values()) - recovery_values)
    if unknown:
        raise StateMachineValidationError(f"Unknown recovery class in mapping: {', '.join(unknown)}")


def validate_state_machine_contracts() -> None:
    validate_transition_table()
    validate_blocker_recovery_mapping()
