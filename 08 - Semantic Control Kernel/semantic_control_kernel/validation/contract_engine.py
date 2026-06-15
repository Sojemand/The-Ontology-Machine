from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from semantic_control_kernel.types.base import KernelContract
from semantic_control_kernel.types.registry import CONTRACT_REGISTRY, ContractRegistryEntry
from semantic_control_kernel.validation.contract_errors import (
    ContractRoundTripError,
    EnumValidationError,
    KernelContractError,
    MissingRequiredFieldError,
    RawDictBoundaryError,
    UnknownSchemaVersionError,
)
from semantic_control_kernel.validation.contract_primitives import (
    matches_kind,
    reject_extensions_field,
    reject_unknown_fields,
    require_required_fields,
    require_schema_version,
    validate_enum,
    values_at_path,
)
from semantic_control_kernel.validation.contract_rules import (
    CLOSED_MAPPING_FIELD_RULES,
    CONSTANT_FIELD_RULES,
    ENUM_FIELD_RULES,
    FIELD_KIND_RULES,
    REQUIRED_FIELD_PATH_RULES,
)
from semantic_control_kernel.validation.contract_schema_rules import validate_schema_specific_rules


def parse_contract(payload: Mapping[str, Any], expected_schema_version: str | None = None) -> KernelContract:
    if not isinstance(payload, Mapping):
        raise KernelContractError("Contract payload must be a mapping.")
    schema_version = _schema_version_from_payload(payload)
    if expected_schema_version is not None:
        require_schema_version(payload, expected_schema_version)
    entry = CONTRACT_REGISTRY.get(schema_version)
    if entry is None:
        raise UnknownSchemaVersionError(f"Unknown contract schema_version: {schema_version}")
    _reject_reference_only_entry(entry)
    copied = deepcopy(dict(payload))
    _validate_payload_against_entry(copied, entry)
    return entry.python_type(copied)


def validate_contract(payload: Mapping[str, Any] | KernelContract, expected_schema_version: str | None = None) -> None:
    if isinstance(payload, KernelContract):
        contract_payload = payload.to_dict()
        if expected_schema_version is not None:
            require_schema_version(contract_payload, expected_schema_version)
        entry = CONTRACT_REGISTRY.get(payload.SCHEMA_VERSION)
        if entry is None:
            raise UnknownSchemaVersionError(f"Unknown contract schema_version: {payload.SCHEMA_VERSION}")
        _reject_reference_only_entry(entry)
        _validate_payload_against_entry(contract_payload, entry)
        return
    parse_contract(payload, expected_schema_version=expected_schema_version)


def serialize_contract(contract: KernelContract) -> dict[str, Any]:
    if not isinstance(contract, KernelContract):
        raise RawDictBoundaryError("serialize_contract requires a typed KernelContract.")
    validate_contract(contract)
    return contract.to_dict()


def validate_contract_roundtrip(contract: KernelContract) -> None:
    if not isinstance(contract, KernelContract):
        raise RawDictBoundaryError("validate_contract_roundtrip requires a typed KernelContract.")
    try:
        serialized = serialize_contract(contract)
        reparsed = parse_contract(serialized, expected_schema_version=contract.SCHEMA_VERSION)
        if serialize_contract(reparsed) != serialized:
            raise ContractRoundTripError(f"{contract.SCHEMA_VERSION} changed during round trip.")
    except KernelContractError:
        raise
    except Exception as exc:  # pragma: no cover - defensive conversion
        raise ContractRoundTripError(str(exc)) from exc


def _schema_version_from_payload(payload: Mapping[str, Any]) -> str:
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        raise MissingRequiredFieldError("Missing required field schema_version.")
    return schema_version


def _validate_payload_against_entry(payload: Mapping[str, Any], entry: ContractRegistryEntry) -> None:
    require_schema_version(payload, entry.schema_version)
    if entry.validation_depth == "reference_only":
        reject_unknown_fields(payload, ("schema_version",), entry.schema_version)
        return
    allowed_fields = set(entry.required_fields) | set(entry.optional_fields)
    require_required_fields(payload, entry.required_fields, entry.schema_version)
    reject_unknown_fields(payload, allowed_fields, entry.schema_version)
    reject_extensions_field(payload, entry.schema_version)
    _validate_required_field_path_rules(payload, entry.schema_version)
    _validate_field_kind_rules(payload, entry.schema_version)
    _validate_closed_mapping_rules(payload, entry.schema_version)
    _validate_enum_rules(payload, entry.schema_version)
    _validate_constant_rules(payload, entry.schema_version)
    validate_schema_specific_rules(payload, entry.schema_version, validate_contract)


def _reject_reference_only_entry(entry: ContractRegistryEntry) -> None:
    if entry.validation_depth == "reference_only":
        raise KernelContractError(
            f"{entry.schema_version} is reference-only and cannot be parsed or serialized as a standalone Kernel object."
        )


def _validate_required_field_path_rules(payload: Mapping[str, Any], schema_version: str) -> None:
    for field_path in REQUIRED_FIELD_PATH_RULES.get(schema_version, ()):
        if not values_at_path(payload, field_path):
            raise MissingRequiredFieldError(
                f"{schema_version} missing required field path {field_path}."
            )


def _validate_field_kind_rules(payload: Mapping[str, Any], schema_version: str) -> None:
    for field_name, expected_kind in FIELD_KIND_RULES.get(schema_version, {}).items():
        if field_name not in payload:
            continue
        if not matches_kind(payload[field_name], expected_kind):
            raise KernelContractError(
                f"{schema_version}.{field_name} must be a {expected_kind}, got {type(payload[field_name]).__name__}."
            )


def _validate_closed_mapping_rules(payload: Mapping[str, Any], schema_version: str) -> None:
    for field_name, allowed_fields in CLOSED_MAPPING_FIELD_RULES.get(schema_version, {}).items():
        if field_name not in payload:
            continue
        value = payload[field_name]
        if not isinstance(value, Mapping):
            raise KernelContractError(f"{schema_version}.{field_name} must be an object.")
        reject_unknown_fields(value, allowed_fields, f"{schema_version}.{field_name}")


def _validate_enum_rules(payload: Mapping[str, Any], schema_version: str) -> None:
    for field_path, enum_values in ENUM_FIELD_RULES.get(schema_version, {}).items():
        values = values_at_path(payload, field_path)
        if not values:
            continue
        for value in values:
            validate_enum(value, enum_values, f"{schema_version}.{field_path}")


def _validate_constant_rules(payload: Mapping[str, Any], schema_version: str) -> None:
    for field_path, expected in CONSTANT_FIELD_RULES.get(schema_version, {}).items():
        values = values_at_path(payload, field_path)
        if not values:
            continue
        for value in values:
            if value != expected:
                raise EnumValidationError(
                    f"{schema_version}.{field_path} must be {expected!r}, got {value!r}."
                )
