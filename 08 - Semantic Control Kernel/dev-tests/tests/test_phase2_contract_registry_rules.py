from __future__ import annotations

import pytest

from semantic_control_kernel.types.registry import CONTRACT_REGISTRY
from semantic_control_kernel.validation.contract_validation import (
    CONSTANT_FIELD_RULES,
    ENUM_FIELD_RULES,
    EnumValidationError,
    KernelContractError,
    MissingRequiredFieldError,
    SchemaVersionMismatchError,
    UnknownFieldError,
    UnknownSchemaVersionError,
    parse_contract,
    serialize_contract,
    validate_contract,
)
from phase2_contract_support import _fixture, _set_path

@pytest.mark.parametrize(
    "schema_version",
    [schema for schema, entry in CONTRACT_REGISTRY.items() if entry.validation_depth != "reference_only"],
)
def test_missing_required_fields_fail(schema_version: str) -> None:
    entry = CONTRACT_REGISTRY[schema_version]
    payload = _fixture(schema_version)
    payload.pop(entry.required_fields[0])

    with pytest.raises(MissingRequiredFieldError):
        validate_contract(payload)

@pytest.mark.parametrize(
    "schema_version",
    [schema for schema, entry in CONTRACT_REGISTRY.items() if entry.extension_policy == "closed_object"],
)
def test_unknown_top_level_fields_fail(schema_version: str) -> None:
    payload = _fixture(schema_version)
    payload["unexpected_phase2_field"] = "example"

    with pytest.raises(UnknownFieldError):
        validate_contract(payload)

@pytest.mark.parametrize(
    "schema_version,field_path",
    [(schema, path) for schema, rules in ENUM_FIELD_RULES.items() for path in rules],
)
def test_enum_valued_fields_reject_unknown_values(schema_version: str, field_path: str) -> None:
    payload = _fixture(schema_version)
    _set_path(payload, field_path, "__invalid_enum__")

    with pytest.raises(EnumValidationError):
        validate_contract(payload)

@pytest.mark.parametrize(
    "schema_version,field_path",
    [(schema, path) for schema, rules in CONSTANT_FIELD_RULES.items() for path in rules],
)
def test_cross_reference_constants_reject_mismatches(schema_version: str, field_path: str) -> None:
    payload = _fixture(schema_version)
    _set_path(payload, field_path, "__wrong_constant__")

    with pytest.raises(EnumValidationError):
        validate_contract(payload)

def test_schema_mismatch_fails() -> None:
    payload = _fixture("kernel.progress_event.v1")

    with pytest.raises(SchemaVersionMismatchError):
        validate_contract(payload, expected_schema_version="kernel.mirror_event.v1")

def test_unknown_schema_version_fails() -> None:
    payload = _fixture("kernel.progress_event.v1")
    payload["schema_version"] = "kernel.unknown_contract.v1"

    with pytest.raises(UnknownSchemaVersionError):
        parse_contract(payload)

def test_reference_only_schema_versions_are_not_standalone_contract_objects() -> None:
    for schema_version, entry in CONTRACT_REGISTRY.items():
        if entry.validation_depth != "reference_only":
            continue
        payload = {"schema_version": schema_version}

        with pytest.raises(KernelContractError, match="reference-only"):
            parse_contract(payload)

        typed_ref = entry.python_type(payload)
        with pytest.raises(KernelContractError, match="reference-only"):
            serialize_contract(typed_ref)

@pytest.mark.parametrize("source_ref", [{}, "interpreter_request_view_vision.v1"])
def test_analyze_sample_source_ref_requires_route_view_kind(source_ref: object) -> None:
    payload = _fixture("kernel.analyze_sample.input.v1")
    payload["source_ref"] = source_ref

    with pytest.raises(MissingRequiredFieldError):
        validate_contract(payload)

def test_extensions_field_is_forbidden_even_inside_nested_payloads() -> None:
    payload = _fixture("kernel.pipeline_batch_manifest.v1")
    payload["active_database"]["extensions"] = {}

    with pytest.raises(UnknownFieldError):
        validate_contract(payload)

def test_closed_deep_pipeline_manifest_rejects_unknown_nested_fields() -> None:
    payload = _fixture("kernel.pipeline_batch_manifest.v1")
    payload["active_database"]["old_database_path_hash"] = "sha256:old"

    with pytest.raises(UnknownFieldError):
        validate_contract(payload)

def test_recovery_dialog_type_is_required_only_for_recovery_dialog() -> None:
    payload = _fixture("kernel.user_interaction_request.v1")
    payload["dialog_type"] = "recovery_dialog"
    payload.pop("recovery_dialog_type", None)

    with pytest.raises(MissingRequiredFieldError):
        validate_contract(payload)

    payload["recovery_dialog_type"] = "stale_lock_dialog"
    validate_contract(payload)

    payload["dialog_type"] = "text_input"
    with pytest.raises(UnknownFieldError):
        validate_contract(payload)
