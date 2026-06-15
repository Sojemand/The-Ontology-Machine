from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_ROOT = PROJECT_ROOT / "config"
BASELINE_ROOT = PROJECT_ROOT / "dev-tests" / "fixtures" / "taxonomy_refactor_baseline"
FROZEN_BASELINE_ROOT = BASELINE_ROOT / "frozen_head"
SNAPSHOT_ROOT = FROZEN_BASELINE_ROOT / "snapshots"
INVENTORY_ROOT = FROZEN_BASELINE_ROOT / "inventories"
FINGERPRINT_MANIFEST_PATH = FROZEN_BASELINE_ROOT / "fingerprint_manifest.json"
CONTRACT_SNAPSHOT_ROOT = FROZEN_BASELINE_ROOT / "contract_snapshots"
CONTRACT_INVENTORY_ROOT = FROZEN_BASELINE_ROOT / "contract_inventories"
CONTRACT_FINGERPRINT_MANIFEST_PATH = FROZEN_BASELINE_ROOT / "contract_fingerprint_manifest.json"
PROVENANCE_PATH = FROZEN_BASELINE_ROOT / "provenance.json"
CLEANUP_MANIFEST_PATH = BASELINE_ROOT / "cleanup_candidates.json"

MASTER_SNAPSHOT_NAME = "normalizer_taxonomy.master.json"
RECIPE_SNAPSHOT_NAME = "semantic_release.recipe.json"
RELEASE_SNAPSHOT_NAME = "semantic_release.normalized.json"
RUNTIME_SNAPSHOT_NAME = "runtime_semantic_assets.normalized.json"
REQUEST_SNAPSHOT_NAME = "request_envelope.01_to_02.json"
STRUCTURED_SNAPSHOT_NAME = "structured_output.02_to_04.json"
NORMALIZED_SNAPSHOT_NAME = "normalized_output.04_to_downstream.json"
PROJECTION_CATALOG_SNAPSHOT_NAME = "projection_catalog.v1.json"
CONTRACT_RELEASE_SNAPSHOT_NAME = "semantic_release.v1.json"
CONTRACT_RUNTIME_SNAPSHOT_NAME = "runtime_semantic_assets.v1.json"
SEMANTIC_STATUS_SNAPSHOT_NAME = "semantic_status.v1.json"
ACTIVE_RELEASE_SNAPSHOT_NAME = "active_semantic_release.v1.json"


def projection_id_from_file_name(file_name: str) -> str:
    return file_name.removeprefix("normalizer_taxonomy.").removesuffix(".json")


def _discover_projection_snapshot_names() -> tuple[str, ...]:
    if SNAPSHOT_ROOT.exists():
        names = sorted(path.name for path in SNAPSHOT_ROOT.glob("normalizer_taxonomy.*.json") if path.name != MASTER_SNAPSHOT_NAME)
        if names:
            return tuple(names)
    return ()


PROJECTION_SNAPSHOT_NAMES = _discover_projection_snapshot_names()
INVENTORY_CASES = (
    ("master_taxonomy", MASTER_SNAPSHOT_NAME, None),
    *(("projection", name, projection_id_from_file_name(name)) for name in PROJECTION_SNAPSHOT_NAMES),
    ("release_recipe", RECIPE_SNAPSHOT_NAME, None),
    ("semantic_release", RELEASE_SNAPSHOT_NAME, None),
    ("runtime_semantic_assets", RUNTIME_SNAPSHOT_NAME, None),
)
CONTRACT_INVENTORY_CASES = (
    ("request_envelope_01_02", REQUEST_SNAPSHOT_NAME, None),
    ("structured_output_02_04", STRUCTURED_SNAPSHOT_NAME, None),
    ("normalized_output_04_downstream", NORMALIZED_SNAPSHOT_NAME, None),
    ("projection_catalog_v1", PROJECTION_CATALOG_SNAPSHOT_NAME, None),
    ("semantic_release_v1", CONTRACT_RELEASE_SNAPSHOT_NAME, None),
    ("runtime_semantic_assets_v1", CONTRACT_RUNTIME_SNAPSHOT_NAME, None),
    ("semantic_status_v1", SEMANTIC_STATUS_SNAPSHOT_NAME, None),
    ("active_semantic_release_v1", ACTIVE_RELEASE_SNAPSHOT_NAME, None),
)
CONTRACT_ARTIFACT_KINDS = frozenset(artifact_kind for artifact_kind, _, _ in CONTRACT_INVENTORY_CASES)
VALID_CLASSIFICATIONS = frozenset({"core", "text", "compiled_only"})
CORE_CLASSIFICATIONS = frozenset({"core"})
PHASE0_ORDERLESS_LIST_KEYS = frozenset({"projection_ids", "available_locales"})
PHASE0_VOLATILE_KEYS = frozenset({"created_at"})
