from __future__ import annotations

from semantic_control_kernel.domain.state_machine.recovery_mapping import BLOCKER_CODES, RECOVERY_BY_BLOCKER
from semantic_control_kernel.domain.state_machine.transition_table import TRANSITION_RULES
from semantic_control_kernel.types.enums import RecoveryStateClass
from semantic_control_kernel.validation.state_machine_validators import validate_state_machine_contracts


def test_every_blocker_code_maps_to_exactly_one_recovery_state_class() -> None:
    validate_state_machine_contracts()

    for code in BLOCKER_CODES:
        assert isinstance(RECOVERY_BY_BLOCKER[code], str)
        assert RECOVERY_BY_BLOCKER[code] in RecoveryStateClass.values()


def test_every_transition_blocker_is_declared_and_no_recovery_class_is_a_blocker_code() -> None:
    referenced = {code for rule in TRANSITION_RULES for code in rule.blocks_if}

    assert referenced <= set(BLOCKER_CODES)
    assert not referenced & set(RecoveryStateClass.values())


def test_every_recovery_state_class_has_at_least_one_detector() -> None:
    mapped_recoveries = set(RECOVERY_BY_BLOCKER.values())

    assert set(RecoveryStateClass.values()) <= mapped_recoveries
