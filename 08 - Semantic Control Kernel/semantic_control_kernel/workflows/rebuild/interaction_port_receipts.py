from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.policy.rebuild_policy import overwrite_receipt_matches
from semantic_control_kernel.repository.receipt_store import ReceiptStore


def matching_overwrite_receipt(
    receipt_store: ReceiptStore,
    target_identity: Mapping[str, Any],
    *,
    artifact_root: str,
    target_database_path: Path,
    loaded_release_fingerprint: str,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    for receipt in reversed(receipt_store.list_by_target(target_identity)):
        payload = receipt.to_dict() if hasattr(receipt, "to_dict") else dict(receipt)
        if overwrite_receipt_matches(
            payload,
            artifact_root=artifact_root,
            target_database_path=target_database_path,
            loaded_release_fingerprint=loaded_release_fingerprint,
            workflow_run_id=workflow_run_id,
        ):
            return dict(payload)
    return None


__all__ = ["matching_overwrite_receipt"]
