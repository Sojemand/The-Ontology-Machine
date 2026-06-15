from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_control_kernel.repository.errors import ImmutableReceiptError
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.types.receipts import ConfirmationReceipt, OperationReceipt, RecoveryReceipt
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
)


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "contracts"


def _fixture(schema_version: str) -> dict:
    return json.loads((FIXTURES / f"{schema_version.replace('.', '__')}.valid.json").read_text(encoding="utf-8"))


def test_receipt_store_appends_confirmation_operation_and_recovery_receipts(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = ReceiptStore(paths)
    confirmation = ConfirmationReceipt.from_dict(_fixture("kernel.confirmation_receipt.v1"))
    operation_payload = _fixture("kernel.operation_receipt.v1")
    operation_payload["workflow_run_id"] = "wr_example"
    operation_payload["target_identity_after"] = {"target_hash": "targethash"}
    operation = OperationReceipt.from_dict(operation_payload)
    recovery = RecoveryReceipt.from_dict(_fixture("kernel.recovery_receipt.v1"))

    store.append_confirmation_receipt(confirmation)
    store.append_operation_receipt(operation)
    store.append_recovery_receipt(recovery)

    assert store.get_receipt("confirmation_receipt_id_example").SCHEMA_VERSION == "kernel.confirmation_receipt.v1"
    assert [receipt.SCHEMA_VERSION for receipt in store.list_by_workflow("wr_example")] == ["kernel.operation_receipt.v1"]
    assert [receipt.SCHEMA_VERSION for receipt in store.list_by_target({"target_hash": "targethash"})] == ["kernel.operation_receipt.v1"]


def test_receipt_store_rejects_duplicate_receipt_ids(tmp_path: Path) -> None:
    store = ReceiptStore(StatePaths.from_state_root(tmp_path / "state"))
    receipt = OperationReceipt.from_dict(_fixture("kernel.operation_receipt.v1"))

    store.append_operation_receipt(receipt)

    with pytest.raises(ImmutableReceiptError):
        store.append_operation_receipt(receipt)


def test_receipt_store_verifies_hashes_and_rebuilds_indexes(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = ReceiptStore(paths)
    payload = _fixture("kernel.operation_receipt.v1")
    payload["workflow_run_id"] = "wr_rebuild"
    receipt = OperationReceipt.from_dict(payload)
    store.append_operation_receipt(receipt)
    for path in paths.receipt_index_by_workflow_dir.glob("*.json"):
        path.unlink()

    store.rebuild_indexes()
    store.assert_receipt_hash("operation_receipt_id_example")

    assert len(store.list_by_workflow("wr_rebuild")) == 1


@pytest.mark.parametrize(
    ("repository_type", "execution"),
    (
        (
            CreationStateRepository,
            lambda state_root: DatabaseCreationExecution(
                workflow_run_id="wr_creation_live_receipt",
                workflow_tool="create_empty_database",
                state_root=state_root,
                final_state="completed",
            ),
        ),
    ),
    ids=("database_creation",),
)
def test_live_workflow_repositories_emit_contract_valid_operation_receipts(
    tmp_path: Path,
    repository_type,
    execution,
) -> None:
    state_root = tmp_path / "state"
    repository = repository_type(state_root)
    live_execution = execution(state_root)

    receipt = repository.append_operation_receipt(
        live_execution,
        function_name="phase3_receipt_boundary_probe",
        final_kernel_state=live_execution.final_state,
    )

    assert receipt.payload["final_kernel_state"] == {"state": "completed"}
    persisted = repository.receipts.get_receipt(receipt.payload["operation_receipt_id"]).to_dict()
    assert persisted["final_kernel_state"] == {"state": "completed"}
