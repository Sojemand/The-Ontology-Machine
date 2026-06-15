from __future__ import annotations

from pathlib import Path
from typing import Any

from semantic_control_kernel.repository._helpers import contract_payload, target_identity_index_key
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore, receipt_payload_hash
from semantic_control_kernel.repository.errors import ImmutableReceiptError, ResumeStateNotFoundError, StateCorruptionError
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.receipt_store_indexes import (
    all_index_refs,
    list_from_index,
    receipt_id,
    receipt_ref,
    rebuild_indexes,
    remove_receipt_refs_from_indexes,
    update_indexes,
)
from semantic_control_kernel.repository.receipt_store_validation import _validate_receipt
from semantic_control_kernel.repository.trace_store import TraceLinkStore
from semantic_control_kernel.types.base import KernelContract
from semantic_control_kernel.types.receipts import ConfirmationReceipt, OperationReceipt, RecoveryReceipt
from semantic_control_kernel.validation.contract_validation import parse_contract


class ReceiptStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "receipts")
        self._trace_store = TraceLinkStore(paths)
        self._hard_cap = KernelStateHardCapService(paths)
        self._index_paths_by_receipt_id: dict[str, set[Path]] = {}
        self._index_records_by_path: dict[Path, tuple[str, str, list[dict[str, Any]]]] = {}

    def append_confirmation_receipt(self, receipt: ConfirmationReceipt) -> None:
        payload = contract_payload(receipt, ConfirmationReceipt)
        self._append_receipt("confirmation", payload["confirmation_receipt_id"], payload, self.paths.receipts_confirmations_dir)

    def append_operation_receipt(self, receipt: OperationReceipt) -> None:
        payload = contract_payload(receipt, OperationReceipt)
        self._append_receipt("operation", payload["operation_receipt_id"], payload, self.paths.receipts_operations_dir)

    def append_recovery_receipt(self, receipt: RecoveryReceipt) -> None:
        payload = contract_payload(receipt, RecoveryReceipt)
        self._append_receipt("recovery", payload["recovery_receipt_id"], payload, self.paths.receipts_recoveries_dir)

    def get_receipt(self, receipt_id_value) -> KernelContract:
        path = self._find_receipt_path(receipt_id_value)
        return parse_contract(self._json.read_json(path, validator=_validate_receipt))

    def list_by_workflow(self, workflow_run_id) -> list[KernelContract]:
        return list_from_index(self, self.paths.receipt_index_by_workflow_dir / f"{require_state_id('workflow_run_id', workflow_run_id)}.json")

    def list_by_target(self, target_identity) -> list[KernelContract]:
        key = target_identity_index_key(target_identity)
        return list_from_index(self, self.paths.receipt_index_by_target_dir / f"{key}.json")

    def assert_receipt_hash(self, receipt_id_value) -> None:
        path = self._find_receipt_path(receipt_id_value)
        payload = self._json.read_json(path, validator=_validate_receipt)
        expected = receipt_payload_hash(payload)
        for ref in all_index_refs(self):
            if ref.get("receipt_id") == receipt_id_value and ref.get("sha256") == expected:
                return
        raise StateCorruptionError(f"Receipt hash index missing or mismatched for {receipt_id_value}")

    def rebuild_indexes(self) -> None:
        rebuild_indexes(self)

    def _append_receipt(self, kind: str, receipt_id_value: str, payload, directory: Path) -> None:
        path = directory / f"{require_state_id(f'{kind}_receipt_id', receipt_id_value)}.json"
        try:
            self._json.write_json(path, payload, immutable=True, validator=_validate_receipt)
        except Exception as exc:
            from semantic_control_kernel.repository.errors import DuplicateStateObjectError

            if isinstance(exc, DuplicateStateObjectError):
                raise ImmutableReceiptError(f"Receipt already exists: {receipt_id_value}") from exc
            raise
        update_indexes(self, receipt_ref(self, kind, receipt_id_value, payload, path), payload)
        self._append_trace_link(kind, receipt_id_value, payload, path)
        deleted_receipt_ids = self._hard_cap.prune_receipts(rebuild_indexes=False)
        if deleted_receipt_ids:
            remove_receipt_refs_from_indexes(self, deleted_receipt_ids)

    def _append_trace_link(self, kind: str, receipt_id_value: str, payload, path: Path) -> None:
        workflow_id = payload.get("workflow_run_id")
        if isinstance(workflow_id, str) and workflow_id and self._trace_store.has_trace_context(workflow_id):
            self._trace_store.append_link_once(
                workflow_run_id=workflow_id,
                object_kind=f"{kind}_receipt",
                object_id=receipt_id_value,
                object_ref=self.paths.relative_to_state_root(path),
            )

    def _find_receipt_path(self, receipt_id_value: str) -> Path:
        for directory in (
            self.paths.receipts_confirmations_dir,
            self.paths.receipts_operations_dir,
            self.paths.receipts_recoveries_dir,
        ):
            path = directory / f"{require_state_id('receipt_id', receipt_id_value)}.json"
            if path.exists():
                return path
        raise ResumeStateNotFoundError(f"Receipt not found: {receipt_id_value}")
