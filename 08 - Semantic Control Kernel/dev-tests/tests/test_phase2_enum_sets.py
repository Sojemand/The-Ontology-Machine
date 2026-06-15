from __future__ import annotations

import pytest

import semantic_control_kernel.types.enums as kernel_enums
from phase2_enum_expectations import EXPECTED_ENUM_VALUES

@pytest.mark.parametrize("enum_name,expected_values", EXPECTED_ENUM_VALUES.items())
def test_phase2_enum_sets_match_build_spec(enum_name: str, expected_values: tuple[str, ...]) -> None:
    enum_type = getattr(kernel_enums, enum_name)

    assert enum_type.values() == expected_values
