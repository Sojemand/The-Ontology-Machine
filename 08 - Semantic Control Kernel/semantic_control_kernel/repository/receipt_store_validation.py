from __future__ import annotations

from semantic_control_kernel.repository.records import ReceiptIndexRecord
from semantic_control_kernel.validation.contract_validation import validate_contract


def _validate_receipt(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Receipt must be an object.")
    validate_contract(payload)


def _validate_receipt_index(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Receipt index must be an object.")
    candidate = payload
    if ReceiptIndexRecord.SCHEMA_VERSION and "schema_version" not in candidate:
        candidate = {**candidate, "schema_version": ReceiptIndexRecord.SCHEMA_VERSION}
    ReceiptIndexRecord._validate(candidate)
