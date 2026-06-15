from __future__ import annotations

from edit_suite.registry.types import ModuleReadinessEntry


class _Entry:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value


class _Textbox:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self, _start: str, _end: str) -> str:
        return self._value


class _Var:
    def __init__(self, value) -> None:
        self._value = value

    def get(self):
        return self._value


class _PathEntry:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def delete(self, _start, _end) -> None:
        self._value = ""

    def insert(self, _index, value: str) -> None:
        self._value = value


def _entry() -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name="03 - Validator",
        display_name="Validator Vision",
        module_root="C:/Validator",
        module_key="validator",
        readiness="ready",
        blockers=(),
        manifest_path="manifest",
        manifest_present=True,
        edit_contract_path="validator_vision/edit_contract",
        runtime_available=True,
    )
