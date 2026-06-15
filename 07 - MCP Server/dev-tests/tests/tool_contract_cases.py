from __future__ import annotations

from tests.tool_contract_matrix_types import GoldenCase
from tests.tool_contract_cases_01 import cases as _cases_01
from tests.tool_contract_cases_02 import cases as _cases_02
from tests.tool_contract_cases_03 import cases as _cases_03
from tests.tool_contract_cases_04 import cases as _cases_04
from tests.tool_contract_cases_05 import cases as _cases_05
from tests.tool_contract_cases_06 import cases as _cases_06
from tests.tool_contract_cases_07 import cases as _cases_07
from tests.tool_contract_cases_08 import cases as _cases_08
from tests.tool_contract_cases_09 import cases as _cases_09
from tests.tool_contract_cases_10 import cases as _cases_10
from tests.tool_contract_cases_11 import cases as _cases_11
from tests.tool_contract_cases_12 import cases as _cases_12
from tests.tool_contract_cases_13 import cases as _cases_13
from tests.tool_contract_cases_14 import cases as _cases_14
from tests.tool_contract_cases_15 import cases as _cases_15
from tests.tool_contract_cases_16 import cases as _cases_16


def golden_cases() -> list[GoldenCase]:
    cases: list[GoldenCase] = []
    cases.extend(_cases_01())
    cases.extend(_cases_02())
    cases.extend(_cases_03())
    cases.extend(_cases_04())
    cases.extend(_cases_05())
    cases.extend(_cases_06())
    cases.extend(_cases_07())
    cases.extend(_cases_08())
    cases.extend(_cases_09())
    cases.extend(_cases_10())
    cases.extend(_cases_11())
    cases.extend(_cases_12())
    cases.extend(_cases_13())
    cases.extend(_cases_14())
    cases.extend(_cases_15())
    cases.extend(_cases_16())
    return cases


GOLDEN_CASES = golden_cases()
