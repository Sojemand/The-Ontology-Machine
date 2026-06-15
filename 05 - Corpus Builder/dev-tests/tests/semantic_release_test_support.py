from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_normalizer_release_bundle(*, project_root: Path | None = None) -> dict[str, object]:
    corpus_project_root = project_root or PROJECT_ROOT
    return deepcopy(_cached_normalizer_release_bundle(str(corpus_project_root.resolve())))


@lru_cache(maxsize=4)
def _cached_normalizer_release_bundle(project_root: str) -> dict[str, object]:
    corpus_project_root = Path(project_root)
    normalizer_root = corpus_project_root.parent / "04 - Normalizer"
    normalizer_site_packages = normalizer_root / "runtime" / "python" / "Lib" / "site-packages"
    if str(normalizer_root) not in sys.path:
        sys.path.insert(0, str(normalizer_root))
    if normalizer_site_packages.is_dir() and str(normalizer_site_packages) not in sys.path:
        sys.path.insert(0, str(normalizer_site_packages))

    from normalizer_vision.runtime_semantic_assets import build_runtime_semantic_assets
    from normalizer_vision.semantic_release import build_semantic_release

    release = build_semantic_release(normalizer_root)
    runtime_assets = build_runtime_semantic_assets(release).to_dict()
    release["projection_catalog"] = runtime_assets["projection_catalog"]
    release["runtime_semantic_assets"] = runtime_assets
    return release


def build_release_variant(
    *,
    project_root: Path | None = None,
    projection_ids: list[str] | None = None,
    master_taxonomy_release_id: str | None = None,
) -> dict[str, object]:
    from corpus_builder.semantic_release import build_release_fingerprint

    release = build_normalizer_release_bundle(project_root=project_root)
    if projection_ids is not None:
        release["projection_ids"] = projection_ids
        release["projections"] = [item for item in release["projections"] if item["projection_id"] in projection_ids]
        release["projection_catalog"]["projections"] = [
            item for item in release["projection_catalog"]["projections"] if item["projection_id"] in projection_ids
        ]
        release["runtime_semantic_assets"]["projection_catalog"]["projections"] = list(release["projection_catalog"]["projections"])
    if master_taxonomy_release_id is not None:
        release["master_taxonomy_release_id"] = master_taxonomy_release_id
        release["projection_catalog"]["master_taxonomy_release_id"] = master_taxonomy_release_id
        release["runtime_semantic_assets"]["master_taxonomy_release_id"] = master_taxonomy_release_id
        release["runtime_semantic_assets"]["projection_catalog"]["master_taxonomy_release_id"] = master_taxonomy_release_id
    _install_dynamic_test_promotion(release)
    release["fingerprint"] = build_release_fingerprint(release)
    release["release_fingerprint"] = release["fingerprint"]
    release["projection_catalog"]["release_fingerprint"] = release["fingerprint"]
    release["runtime_semantic_assets"]["release_fingerprint"] = release["fingerprint"]
    release["runtime_semantic_assets"]["projection_catalog"]["release_fingerprint"] = release["fingerprint"]
    release["runtime_semantic_assets"]["vision_policy_bundle"]["release_fingerprint"] = release["fingerprint"]
    return release


def _install_dynamic_test_promotion(release: dict[str, object]) -> None:
    slot = {
        "slot": "billing_reference",
        "label": "Billing Reference",
        "value_type": "string",
        "scope": "document",
        "cardinality": "single",
        "query_role": "identifier",
        "display_rank": 10,
    }
    rule = {
        "slot": "billing_reference",
        "source_paths": ["content.fields.reference_number", "content.fields.invoice_number", "content.fields.document_number"],
    }
    master = release.get("master_taxonomy")
    if isinstance(master, dict):
        slots = [deepcopy(item) for item in master.get("promotion_slots", []) or [] if isinstance(item, dict)]
        if not any(item.get("slot") == slot["slot"] for item in slots):
            slots.append(slot)
        master["promotion_slots"] = slots
    for projection in release.get("projections", []) or []:
        if not isinstance(projection, dict):
            continue
        include_fields = {str(code) for code in projection.get("include_field_codes", []) or []}
        rules = [deepcopy(item) for item in projection.get("promotion_rules", []) or [] if isinstance(item, dict)]
        if include_fields & {"invoice_number", "document_number"} and not any(item.get("slot") == rule["slot"] for item in rules):
            rules.append(rule)
        projection["promotion_rules"] = rules
    _sync_embedded_dynamic_test_promotion(release, slot, rule)


def _sync_embedded_dynamic_test_promotion(
    release: dict[str, object],
    slot: dict[str, object],
    rule: dict[str, object],
) -> None:
    runtime_assets = release.get("runtime_semantic_assets")
    if isinstance(runtime_assets, dict):
        master = release.get("master_taxonomy")
        if isinstance(master, dict):
            runtime_assets["promotion_slots"] = deepcopy(master.get("promotion_slots", []) or [])
    catalogs = [release.get("projection_catalog")]
    if isinstance(runtime_assets, dict):
        catalogs.append(runtime_assets.get("projection_catalog"))
    projection_rules = {
        str(item.get("projection_id") or ""): deepcopy(item.get("promotion_rules", []) or [])
        for item in release.get("projections", []) or []
        if isinstance(item, dict)
    }
    for catalog in catalogs:
        if not isinstance(catalog, dict):
            continue
        for projection in catalog.get("projections", []) or []:
            if not isinstance(projection, dict):
                continue
            rules = projection_rules.get(str(projection.get("projection_id") or ""), [])
            projection["promotion_rules"] = deepcopy(rules)
            field_slot_map = dict(projection.get("field_slot_map") or {})
            if any(item.get("slot") == rule["slot"] for item in rules if isinstance(item, dict)):
                field_slot_map.update({
                    "reference_number": "billing_reference",
                    "invoice_number": "billing_reference",
                    "document_number": "billing_reference",
                })
            projection["field_slot_map"] = field_slot_map
