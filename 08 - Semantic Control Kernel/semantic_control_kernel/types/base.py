from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, ClassVar, Mapping, TypeVar


def _copy_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(payload))


@dataclass(frozen=True)
class KernelContract:
    payload: dict[str, Any] = field(default_factory=dict)

    SCHEMA_VERSION: ClassVar[str] = ""

    def __post_init__(self) -> None:
        copied = _copy_payload(self.payload)
        if self.SCHEMA_VERSION and "schema_version" not in copied:
            copied["schema_version"] = self.SCHEMA_VERSION
        object.__setattr__(self, "payload", copied)

    @property
    def schema_version(self) -> str:
        value = self.payload.get("schema_version", self.SCHEMA_VERSION)
        return value if isinstance(value, str) else self.SCHEMA_VERSION

    @classmethod
    def from_dict(cls: type[ContractT], payload: Mapping[str, Any]) -> ContractT:
        from semantic_control_kernel.validation.contract_validation import parse_contract

        parsed = parse_contract(payload, expected_schema_version=cls.SCHEMA_VERSION)
        if not isinstance(parsed, cls):
            raise TypeError(f"Parsed contract is not {cls.__name__}.")
        return parsed

    def to_dict(self) -> dict[str, Any]:
        return _copy_payload({**self.payload, "schema_version": self.SCHEMA_VERSION})

    def validate(self) -> None:
        from semantic_control_kernel.validation.contract_validation import validate_contract

        validate_contract(self, expected_schema_version=self.SCHEMA_VERSION)


@dataclass(frozen=True)
class ContractRef(KernelContract):
    pass


ContractT = TypeVar("ContractT", bound=KernelContract)


def make_contract_type(type_name: str, schema_version: str, module_name: str) -> type[KernelContract]:
    namespace: dict[str, Any] = {
        "__module__": module_name,
        "SCHEMA_VERSION": schema_version,
    }
    return dataclass(frozen=True)(type(type_name, (KernelContract,), namespace))


def make_contract_types(rows: tuple[tuple[str, str], ...], module_name: str) -> dict[str, type[KernelContract]]:
    return {name: make_contract_type(name, schema_version, module_name) for name, schema_version in rows}


def make_contract_ref_type(type_name: str, schema_version: str, module_name: str) -> type[ContractRef]:
    namespace: dict[str, Any] = {
        "__module__": module_name,
        "SCHEMA_VERSION": schema_version,
    }
    return dataclass(frozen=True)(type(type_name, (ContractRef,), namespace))
