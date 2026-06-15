from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from semantic_control_kernel.types.base import KernelContract
from semantic_control_kernel.validation.contract_validation import RawDictBoundaryError, parse_contract


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    MODULE_ROOT
    / "dev-tests"
    / "fixtures"
    / "contracts"
    / "kernel__progress_event__v1.valid.json"
)


class WorkflowFake:
    def __init__(self, repository: "RepositoryFake") -> None:
        self.repository = repository

    def run(self, contract: KernelContract) -> None:
        if isinstance(contract, Mapping):
            raise RawDictBoundaryError("surface-to-workflow boundary received raw dict.")
        if not isinstance(contract, KernelContract):
            raise RawDictBoundaryError("surface-to-workflow boundary requires a typed contract.")
        self.repository.save(contract)


class RepositoryFake:
    def save(self, contract: KernelContract) -> None:
        if isinstance(contract, Mapping):
            raise RawDictBoundaryError("workflow-to-repository boundary received raw dict.")
        if not isinstance(contract, KernelContract):
            raise RawDictBoundaryError("workflow-to-repository boundary requires a typed contract.")


def _raw_payload() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_raw_json_is_accepted_only_at_parse_boundary() -> None:
    raw_payload = _raw_payload()

    contract = parse_contract(raw_payload)

    assert isinstance(contract, KernelContract)


def test_surface_to_workflow_boundary_rejects_raw_dict() -> None:
    workflow = WorkflowFake(RepositoryFake())

    with pytest.raises(RawDictBoundaryError):
        workflow.run(_raw_payload())  # type: ignore[arg-type]


def test_workflow_to_repository_boundary_rejects_raw_dict() -> None:
    repository = RepositoryFake()

    with pytest.raises(RawDictBoundaryError):
        repository.save(_raw_payload())  # type: ignore[arg-type]


def test_typed_contracts_are_accepted_after_parse_boundary() -> None:
    workflow = WorkflowFake(RepositoryFake())
    contract = parse_contract(_raw_payload())

    workflow.run(contract)
