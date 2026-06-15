from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from semantic_control_kernel.types.client_frontend_events import (
    validate_client_frontend_event,
    validate_client_frontend_event_ack,
)
from semantic_control_kernel.types.interaction import (
    validate_user_interaction_request,
    validate_user_interaction_response,
)
from semantic_control_kernel.types.registry import CONTRACT_REGISTRY
from semantic_control_kernel.validation.contract_validation import (
    CONSTANT_FIELD_RULES,
    ENUM_FIELD_RULES,
    KernelContractError,
    UnknownFieldError,
    validate_contract,
)
from phase2_contract_support import FIXTURE_ROOT, _fixture, _fixture_prefix

def test_fixtures_are_not_mutated_by_contract_validation() -> None:
    payload = _fixture("kernel.progress_event.v1")
    original = deepcopy(payload)

    validate_contract(payload)

    assert payload == original

def test_runtime_surface_contract_fixtures_match_live_validators() -> None:
    validate_user_interaction_request(_fixture("kernel.user_interaction_request.v1"))
    validate_user_interaction_response(_fixture("kernel.user_interaction_response.v1"))
    validate_client_frontend_event(_fixture("kernel.client_frontend_event.v1"))
    validate_client_frontend_event_ack(_fixture("kernel.client_frontend_event_ack.v1"))

@pytest.mark.parametrize(
    "schema_version,field_name",
    (
        ("kernel.user_interaction_request.v1", "state_snapshot_identity"),
        ("kernel.user_interaction_response.v1", "state_snapshot_identity"),
        ("kernel.confirmation_request.v1", "state_snapshot_identity"),
        ("kernel.confirmation_receipt.v1", "confirmed_state_snapshot_identity"),
        ("kernel.workflow_resume_state.v1", "state_snapshot_identity"),
        ("kernel.database_merge_reconciliation_receipt.v1", "state_snapshot_identity"),
        ("kernel.recovery_option.v1", "state_snapshot_identity"),
        ("kernel.recovery_receipt.v1", "state_snapshot_identity"),
    ),
)
def test_state_snapshot_identity_rejects_unknown_nested_fields(
    schema_version: str,
    field_name: str,
) -> None:
    payload = _fixture(schema_version)
    payload[field_name]["unexpected_nested_phase2_field"] = "example"

    with pytest.raises(UnknownFieldError):
        validate_contract(payload)

@pytest.mark.parametrize(
    "schema_version,field_name",
    (
        ("kernel.user_interaction_request.v1", "target_identity"),
        ("kernel.user_interaction_response.v1", "target_identity"),
        ("kernel.confirmation_request.v1", "target_identity"),
        ("kernel.confirmation_receipt.v1", "confirmed_target_identity"),
        ("kernel.lock_state.v1", "target_identity"),
        ("kernel.operation_receipt.v1", "target_identity_before"),
        ("kernel.operation_receipt.v1", "target_identity_after"),
        ("kernel.database_merge_reconciliation_receipt.v1", "target_identity"),
        ("kernel.recovery_option.v1", "target_identity"),
        ("kernel.recovery_receipt.v1", "target_identity_before"),
        ("kernel.recovery_receipt.v1", "target_identity_after"),
    ),
)
def test_target_identity_rejects_unknown_nested_fields(schema_version: str, field_name: str) -> None:
    payload = _fixture(schema_version)
    payload[field_name]["unexpected_nested_phase2_field"] = "example"

    with pytest.raises(UnknownFieldError):
        validate_contract(payload)

def test_user_interaction_request_requires_string_response_shape() -> None:
    payload = _fixture("kernel.user_interaction_request.v1")
    payload["response_shape"] = {"path_value": True}

    with pytest.raises(KernelContractError):
        validate_contract(payload)

def test_user_interaction_request_requires_structured_expiration_policy() -> None:
    payload = _fixture("kernel.user_interaction_request.v1")
    payload["expiration_policy"] = "selection_short"

    with pytest.raises(KernelContractError):
        validate_contract(payload)

    payload = _fixture("kernel.user_interaction_request.v1")
    payload["expiration_policy"]["unexpected_nested_phase2_field"] = True

    with pytest.raises(UnknownFieldError):
        validate_contract(payload)

@pytest.mark.parametrize(
    "schema_version",
    (
        "kernel.user_interaction_response.v1",
        "kernel.confirmation_receipt.v1",
        "kernel.client_frontend_event_ack.v1",
    ),
)
def test_host_surface_identity_must_be_a_string(schema_version: str) -> None:
    field_name = "host_surface_identity"
    payload = _fixture(schema_version)
    payload[field_name] = {"id": "wrong_shape"}

    with pytest.raises(KernelContractError):
        validate_contract(payload)

def test_lock_state_requires_structured_expiry_policy() -> None:
    payload = _fixture("kernel.lock_state.v1")
    payload["expiry_policy"] = "2026-05-05T00:15:00Z"

    with pytest.raises(KernelContractError):
        validate_contract(payload)

    payload = _fixture("kernel.lock_state.v1")
    payload["expiry_policy"]["unexpected_nested_phase2_field"] = "example"

    with pytest.raises(UnknownFieldError):
        validate_contract(payload)

def test_client_frontend_event_validates_embedded_contract_shape() -> None:
    payload = _fixture("kernel.client_frontend_event.v1")
    payload["interaction_request"]["state_snapshot_identity"]["unexpected_nested_phase2_field"] = "example"

    with pytest.raises(UnknownFieldError):
        validate_client_frontend_event(payload)

def test_client_frontend_event_batch_validates_embedded_events() -> None:
    payload = _fixture("kernel.client_frontend_event_batch.v1")
    payload["events"][0]["interaction_request"]["response_shape"] = {"bad": True}

    with pytest.raises(KernelContractError):
        validate_contract(payload)

def test_required_invalid_fixture_inventory_is_present() -> None:
    actual = {path.name for path in FIXTURE_ROOT.glob("*.invalid.*.json")}
    expected: set[str] = set()
    for schema_version, entry in CONTRACT_REGISTRY.items():
        if entry.validation_depth == "reference_only":
            continue
        prefix = _fixture_prefix(schema_version)
        if entry.required_fields:
            expected.add(f"{prefix}.invalid.missing_required.json")
        if entry.extension_policy == "closed_object":
            expected.add(f"{prefix}.invalid.unknown_field.json")
        if schema_version in ENUM_FIELD_RULES or schema_version in CONSTANT_FIELD_RULES:
            expected.add(f"{prefix}.invalid.enum_mismatch.json")

    assert expected <= actual

@pytest.mark.parametrize("path", sorted(FIXTURE_ROOT.glob("*.invalid.*.json")), ids=lambda path: path.name)
def test_invalid_fixtures_fail_contract_validation(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))

    with pytest.raises(KernelContractError):
        validate_contract(payload)
