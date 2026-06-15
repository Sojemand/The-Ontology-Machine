from __future__ import annotations

from semantic_control_kernel.types.base import make_contract_types


_CONTRACT_TYPES = (
    ("ConfirmationRequest", "kernel.confirmation_request.v1"),
    ("ConfirmationReceipt", "kernel.confirmation_receipt.v1"),
    ("DatabaseMergeReconciliationReceipt", "kernel.database_merge_reconciliation_receipt.v1"),
    ("OperationReceipt", "kernel.operation_receipt.v1"),
    ("RecoveryReceipt", "kernel.recovery_receipt.v1"),
)

globals().update(make_contract_types(_CONTRACT_TYPES, __name__))
