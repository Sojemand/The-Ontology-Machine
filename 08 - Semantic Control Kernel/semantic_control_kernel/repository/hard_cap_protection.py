from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

from semantic_control_kernel.repository.hard_cap_file_ops import path_sort_key
from semantic_control_kernel.repository.paths import StatePaths

if TYPE_CHECKING:
    from semantic_control_kernel.repository.atomic_json import AtomicJsonStore


def support_bundle_manifests(paths: StatePaths, json_store: AtomicJsonStore) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(paths.support_bundles_dir.glob("*/support_bundle_manifest.json"), key=path_sort_key):
        manifests.append(json_store.read_json(path))
    return manifests


def support_bundle_relative_child_names(paths: StatePaths, json_store: AtomicJsonStore, prefix: str) -> set[str]:
    child_names: set[str] = set()
    for manifest in support_bundle_manifests(paths, json_store):
        for text in iter_strings(manifest):
            if not text.startswith(prefix + "/"):
                continue
            first = text[len(prefix) + 1 :].split("/", 1)[0].strip()
            if first:
                child_names.add(first)
    return child_names


def protected_receipt_ids(paths: StatePaths, json_store: AtomicJsonStore) -> set[str]:
    protected: set[str] = set()
    _collect_artifact_tree_receipts(paths, json_store, protected)
    _collect_binding_receipts(paths, json_store, protected)
    _collect_attach_receipts(paths, json_store, protected)
    _collect_lock_receipts(paths, json_store, protected)
    for manifest in support_bundle_manifests(paths, json_store):
        collect_receipt_ids(protected, manifest.get("related_receipt_refs"))
    return protected


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, Mapping):
        for item in value.values():
            yield from iter_strings(item)
        return
    if isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def collect_receipt_ids(target: set[str], value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"receipt_id", "confirmation_receipt_id", "operation_receipt_id", "recovery_receipt_id"}:
                add_if_string(target, item)
            else:
                collect_receipt_ids(target, item)
        return
    if isinstance(value, list):
        for item in value:
            collect_receipt_ids(target, item)


def add_if_string(target: set[str], value: Any) -> None:
    if isinstance(value, str) and value.strip():
        target.add(value.strip())


def add_string_sequence(target: set[str], value: Any) -> None:
    if isinstance(value, list):
        for item in value:
            add_if_string(target, item)


def _collect_artifact_tree_receipts(paths: StatePaths, json_store: AtomicJsonStore, protected: set[str]) -> None:
    for path in paths.artifact_trees_active_dir.glob("*.json"):
        payload = json_store.read_json(path)
        add_if_string(protected, payload.get("validation_receipt_id"))
        add_string_sequence(protected, payload.get("evidence_refs"))


def _collect_binding_receipts(paths: StatePaths, json_store: AtomicJsonStore, protected: set[str]) -> None:
    for path in paths.bindings_records_dir.glob("*.json"):
        provenance = json_store.read_json(path).get("binding_provenance")
        if isinstance(provenance, Mapping):
            add_string_sequence(protected, provenance.get("evidence_refs"))


def _collect_attach_receipts(paths: StatePaths, json_store: AtomicJsonStore, protected: set[str]) -> None:
    for path in paths.attach_states_by_database_dir.glob("*.json"):
        add_if_string(protected, json_store.read_json(path).get("attach_receipt_id"))


def _collect_lock_receipts(paths: StatePaths, json_store: AtomicJsonStore, protected: set[str]) -> None:
    for path in paths.locks_active_dir.glob("*.json"):
        evidence = json_store.read_json(path).get("liveness_evidence")
        if not isinstance(evidence, Mapping):
            continue
        for key in ("release_receipt_ref", "failure_receipt_ref"):
            receipt_ref = evidence.get(key)
            if isinstance(receipt_ref, Mapping):
                collect_receipt_ids(protected, receipt_ref)
