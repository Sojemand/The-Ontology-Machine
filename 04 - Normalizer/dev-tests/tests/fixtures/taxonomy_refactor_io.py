from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tests.fixtures.taxonomy_refactor_paths import (
    CLEANUP_MANIFEST_PATH,
    CONFIG_ROOT,
    CONTRACT_FINGERPRINT_MANIFEST_PATH,
    CONTRACT_INVENTORY_ROOT,
    CONTRACT_SNAPSHOT_ROOT,
    FINGERPRINT_MANIFEST_PATH,
    INVENTORY_ROOT,
    PHASE0_ORDERLESS_LIST_KEYS,
    PHASE0_VOLATILE_KEYS,
    PROJECTION_SNAPSHOT_NAMES,
    PROJECT_ROOT,
    PROVENANCE_PATH,
    RECIPE_SNAPSHOT_NAME,
    RELEASE_SNAPSHOT_NAME,
    RUNTIME_SNAPSHOT_NAME,
    SNAPSHOT_ROOT,
    MASTER_SNAPSHOT_NAME,
    projection_id_from_file_name,
)


def inventory_file_name(snapshot_name: str) -> str:
    return snapshot_name.replace(".json", ".inventory.json")


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(payload: Any) -> str:
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_release_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))
    normalized.pop("created_at", None)
    return normalized


def normalize_phase0_comparison_payload(payload: Any) -> Any:
    return _normalize_phase0_value(json.loads(json.dumps(payload)))


def normalize_phase0_release_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_phase0_comparison_payload(payload)
    if not isinstance(normalized, dict):
        raise TypeError("normalize_phase0_release_payload erwartet ein JSON-Objekt.")
    return normalized


def normalize_phase0_runtime_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_phase0_comparison_payload(payload)
    if not isinstance(normalized, dict):
        raise TypeError("normalize_phase0_runtime_payload erwartet ein JSON-Objekt.")
    return normalized


def live_snapshot_payloads() -> dict[str, Any]:
    from normalizer_vision.runtime_semantic_assets import build_runtime_semantic_assets
    from normalizer_vision.semantic_release import build_semantic_release
    from normalizer_vision.taxonomy_compile import compile_source_package
    from normalizer_vision.taxonomy_sources import load_source_package

    compiled = compile_source_package(load_source_package(PROJECT_ROOT))
    payloads = {MASTER_SNAPSHOT_NAME: compiled.master}
    for name in PROJECTION_SNAPSHOT_NAMES:
        payloads[name] = compiled.projections[projection_id_from_file_name(name)]
    payloads[RECIPE_SNAPSHOT_NAME] = load_json(CONFIG_ROOT / RECIPE_SNAPSHOT_NAME)
    release = build_semantic_release(PROJECT_ROOT)
    payloads[RELEASE_SNAPSHOT_NAME] = normalize_release_payload(release)
    payloads[RUNTIME_SNAPSHOT_NAME] = build_runtime_semantic_assets(release).to_dict()
    return payloads


def load_snapshot_payload(snapshot_name: str) -> Any:
    return load_json(SNAPSHOT_ROOT / snapshot_name)


def load_inventory_entries(snapshot_name: str) -> list[dict[str, str]]:
    return load_json(INVENTORY_ROOT / inventory_file_name(snapshot_name))


def load_fingerprint_manifest() -> dict[str, str]:
    return load_json(FINGERPRINT_MANIFEST_PATH)


def load_contract_snapshot_payload(snapshot_name: str) -> Any:
    return load_json(CONTRACT_SNAPSHOT_ROOT / snapshot_name)


def load_contract_inventory_entries(snapshot_name: str) -> list[dict[str, str]]:
    return load_json(CONTRACT_INVENTORY_ROOT / inventory_file_name(snapshot_name))


def load_contract_fingerprint_manifest() -> dict[str, str]:
    return load_json(CONTRACT_FINGERPRINT_MANIFEST_PATH)


def load_cleanup_manifest() -> list[dict[str, str]]:
    return load_json(CLEANUP_MANIFEST_PATH)


def load_provenance() -> dict[str, Any]:
    return load_json(PROVENANCE_PATH)


def _normalize_phase0_value(value: Any, *, parent_key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize_phase0_value(item, parent_key=key)
            for key, item in value.items()
            if key not in PHASE0_VOLATILE_KEYS
        }
    if isinstance(value, list):
        normalized_items = [_normalize_phase0_value(item, parent_key=parent_key) for item in value]
        if parent_key in PHASE0_ORDERLESS_LIST_KEYS:
            return sorted(normalized_items, key=canonical_json)
        if parent_key == "projections" and all(isinstance(item, dict) and str(item.get("projection_id") or "").strip() for item in normalized_items):
            return sorted(normalized_items, key=lambda item: str(item["projection_id"]))
        return normalized_items
    return value
