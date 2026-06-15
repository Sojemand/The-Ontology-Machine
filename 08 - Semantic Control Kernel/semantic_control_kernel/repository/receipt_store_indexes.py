from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from semantic_control_kernel.repository._helpers import target_identity_index_key
from semantic_control_kernel.repository.atomic_json import receipt_payload_hash
from semantic_control_kernel.repository.errors import StateCorruptionError
from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.repository.records import ReceiptIndexRecord
from semantic_control_kernel.repository.receipt_store_validation import (
    _validate_receipt,
    _validate_receipt_index,
)
from semantic_control_kernel.validation.contract_validation import parse_contract


def rebuild_indexes(store) -> None:
    store._index_paths_by_receipt_id.clear()
    store._index_records_by_path.clear()
    grouped_refs: dict[tuple[Path, str, str], list[dict[str, Any]]] = {}
    for kind, directory in (
        ("confirmation", store.paths.receipts_confirmations_dir),
        ("operation", store.paths.receipts_operations_dir),
        ("recovery", store.paths.receipts_recoveries_dir),
    ):
        for path in sorted(directory.glob("*.json")):
            payload = store._json.read_json(path, validator=_validate_receipt)
            ref = receipt_ref(store, kind, receipt_id(payload), payload, path)
            collect_index_refs(store, grouped_refs, ref, payload)
    clear_index_dir(store, store.paths.receipt_index_by_workflow_dir)
    clear_index_dir(store, store.paths.receipt_index_by_target_dir)
    rebuilt_at = utc_iso()
    for (path, index_kind, index_key), refs in sorted(grouped_refs.items(), key=lambda item: str(item[0][0])):
        write_index_record(store, path, index_kind, index_key, refs, rebuilt_at=rebuilt_at)


def receipt_ref(store, kind: str, receipt_id_value: str, payload: Mapping[str, Any], path: Path) -> dict[str, Any]:
    return {
        "receipt_id": receipt_id_value,
        "receipt_kind": kind,
        "receipt_path": store.paths.relative_to_state_root(path),
        "sha256": receipt_payload_hash(payload),
    }


def update_indexes(store, receipt_ref_payload: dict[str, Any], payload: Mapping[str, Any]) -> None:
    for path, index_kind, index_key in index_specs(store, payload):
        append_index_ref(store, path, index_kind, index_key, receipt_ref_payload)


def index_specs(store, payload: Mapping[str, Any]) -> list[tuple[Path, str, str]]:
    specs: list[tuple[Path, str, str]] = []
    workflow_id = payload.get("workflow_run_id")
    if isinstance(workflow_id, str) and workflow_id:
        workflow_id = require_state_id("workflow_run_id", workflow_id)
        specs.append((store.paths.receipt_index_by_workflow_dir / f"{workflow_id}.json", "by_workflow", workflow_id))
    target_keys: set[str] = set()
    for target in receipt_targets(payload):
        key = str(target_identity_index_key(target) or "")
        if key and key not in target_keys:
            target_keys.add(key)
            specs.append((store.paths.receipt_index_by_target_dir / f"{key}.json", "by_target", key))
    return specs


def collect_index_refs(store, grouped_refs: dict[tuple[Path, str, str], list[dict[str, Any]]], receipt_ref_payload: dict[str, Any], payload: Mapping[str, Any]) -> None:
    for path, index_kind, index_key in index_specs(store, payload):
        grouped_refs.setdefault((path, index_kind, index_key), []).append(receipt_ref_payload)


def append_index_ref(store, path: Path, index_kind: str, index_key: str, receipt_ref_payload: dict[str, Any]) -> None:
    cached = store._index_records_by_path.get(path)
    if cached is not None:
        refs = [dict(ref) for ref in cached[2] if ref.get("receipt_id") != receipt_ref_payload["receipt_id"]]
    elif path.exists():
        record = ReceiptIndexRecord.from_dict(store._json.read_json(path, validator=_validate_receipt_index))
        refs = [ref for ref in record.receipt_refs if ref.get("receipt_id") != receipt_ref_payload["receipt_id"]]
    else:
        refs = []
    refs.append(receipt_ref_payload)
    write_index_record(store, path, index_kind, index_key, refs)
    store._index_records_by_path[path] = (index_kind, index_key, [dict(ref) for ref in refs])
    store._index_paths_by_receipt_id.setdefault(str(receipt_ref_payload["receipt_id"]), set()).add(path)


def write_index_record(store, path: Path, index_kind: str, index_key: str, receipt_refs: list[dict[str, Any]], *, rebuilt_at: str | None = None) -> None:
    payload = {
        "index_key": index_key,
        "index_kind": index_kind,
        "receipt_refs": receipt_refs,
        "rebuilt_at": rebuilt_at or utc_iso(),
        "schema_version": ReceiptIndexRecord.SCHEMA_VERSION,
    }
    store._json.write_json(path, payload, validator=_validate_receipt_index, sync_to_disk=False, read_back=False, file_lock=False)


def list_from_index(store, path: Path) -> list:
    if not path.exists():
        return []
    try:
        record = ReceiptIndexRecord.from_dict(store._json.read_json(path, validator=_validate_receipt_index))
    except StateCorruptionError:
        store.rebuild_indexes()
        if not path.exists():
            return []
        record = ReceiptIndexRecord.from_dict(store._json.read_json(path, validator=_validate_receipt_index))
    receipts = []
    for ref in record.receipt_refs:
        receipt_path = store.paths.safe_path(ref["receipt_path"])
        receipts.append(parse_contract(store._json.read_json(receipt_path, validator=_validate_receipt)))
    return receipts


def remove_receipt_refs_from_indexes(store, receipt_ids: set[str]) -> None:
    if receipt_ids and all(receipt_id in store._index_paths_by_receipt_id for receipt_id in receipt_ids):
        paths = {path for receipt_id in receipt_ids for path in store._index_paths_by_receipt_id.get(receipt_id, set())}
    else:
        paths = {path for directory in (store.paths.receipt_index_by_workflow_dir, store.paths.receipt_index_by_target_dir) for path in directory.glob("*.json")}
    changed_at = utc_iso()
    for path in sorted(paths):
        if path.exists() and not remove_receipt_refs_from_index_path(store, path, receipt_ids, changed_at):
            return
    for receipt_id_value in receipt_ids:
        store._index_paths_by_receipt_id.pop(receipt_id_value, None)


def remove_receipt_refs_from_index_path(store, path: Path, receipt_ids: set[str], changed_at: str) -> bool:
    cached = store._index_records_by_path.get(path)
    if cached is None:
        try:
            record = ReceiptIndexRecord.from_dict(store._json.read_json(path, validator=_validate_receipt_index))
        except StateCorruptionError:
            store.rebuild_indexes()
            return False
        index_kind, index_key, existing_refs = record.index_kind, record.index_key, list(record.receipt_refs)
    else:
        index_kind, index_key, existing_refs = cached
    refs = [ref for ref in existing_refs if ref.get("receipt_id") not in receipt_ids]
    if len(refs) == len(existing_refs):
        return True
    if not refs:
        store._json.delete_json(path)
        store._index_records_by_path.pop(path, None)
        return True
    write_index_record(store, path, index_kind, index_key, refs, rebuilt_at=changed_at)
    store._index_records_by_path[path] = (index_kind, index_key, [dict(ref) for ref in refs])
    return True


def all_index_refs(store) -> list[dict[str, Any]]:
    refs = []
    for directory in (store.paths.receipt_index_by_workflow_dir, store.paths.receipt_index_by_target_dir):
        for path in sorted(directory.glob("*.json")):
            try:
                refs.extend(ReceiptIndexRecord.from_dict(store._json.read_json(path, validator=_validate_receipt_index)).receipt_refs)
            except StateCorruptionError:
                continue
    return refs


def clear_index_dir(store, directory: Path) -> None:
    for path in sorted(directory.glob("*.json")):
        store._json.delete_json(path)
        store._index_records_by_path.pop(path, None)


def receipt_targets(payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for key in ("confirmed_target_identity", "target_identity_before", "target_identity_after"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            yield value


def receipt_id(payload: Mapping[str, Any]) -> str:
    for key in ("confirmation_receipt_id", "operation_receipt_id", "recovery_receipt_id"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    raise StateCorruptionError("Receipt payload does not contain a known receipt ID.")
