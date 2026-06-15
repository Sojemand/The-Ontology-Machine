from __future__ import annotations

from semantic_control_kernel.types.enums import RecoveryStateClass


RECOVERY_STATE_CLASSES: tuple[str, ...] = RecoveryStateClass.values()


def is_recovery_state_class(value: str) -> bool:
    return value in RECOVERY_STATE_CLASSES
