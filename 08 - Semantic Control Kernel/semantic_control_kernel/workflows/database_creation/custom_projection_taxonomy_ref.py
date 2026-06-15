from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.policy.runtime_locale import control_locale_or_default
from semantic_control_kernel.workflows.database_creation.custom_projection_taxonomy_helpers import (
    TAXONOMY_CODE_SECTIONS,
    taxonomy_allowed_codes,
    taxonomy_fallback_codes,
    taxonomy_promotion_slots,
    taxonomy_term_summaries,
)


def taxonomy_ref_for_projection_authoring(
    taxonomy_ref: Mapping[str, Any],
    *,
    release_path: str | Path | None = None,
) -> dict[str, Any]:
    enriched = deepcopy(dict(taxonomy_ref))
    release = _read_release_payload(release_path)
    release_taxonomy_ref = release.get("taxonomy_ref")
    if isinstance(release_taxonomy_ref, Mapping):
        for key in ("allowed_codes", "fallback_codes", "term_summaries", "promotion_slots"):
            if key not in enriched and key in release_taxonomy_ref:
                enriched[key] = deepcopy(release_taxonomy_ref[key])
    master = release.get("master_taxonomy")
    if isinstance(master, Mapping):
        _merge_master_taxonomy(enriched, release, master)
    _merge_taxonomy_core_sections(enriched)
    allowed_codes = taxonomy_allowed_codes(enriched)
    enriched["allowed_codes"] = sorted(allowed_codes)
    enriched["fallback_codes"] = sorted(taxonomy_fallback_codes(enriched, allowed_codes))
    enriched["term_summaries"] = taxonomy_term_summaries(enriched, allowed_codes)
    enriched["promotion_slots"] = taxonomy_promotion_slots(enriched)
    return enriched


def _read_release_payload(release_path: str | Path | None) -> dict[str, Any]:
    if not release_path:
        return {}
    path = Path(release_path)
    if path.is_dir():
        path = path / "release.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _merge_master_taxonomy(enriched: dict[str, Any], release: Mapping[str, Any], master: Mapping[str, Any]) -> None:
    for key in TAXONOMY_CODE_SECTIONS:
        if isinstance(master.get(key), list):
            enriched[key] = deepcopy(master[key])
    defaults = master.get("defaults")
    if isinstance(defaults, Mapping):
        enriched["defaults"] = deepcopy(defaults)
    promotion_slots = master.get("promotion_slots")
    if isinstance(promotion_slots, list):
        enriched["promotion_slots"] = deepcopy(promotion_slots)
    enriched.setdefault("runtime_locale", control_locale_or_default(release.get("runtime_locale")))
    enriched.setdefault(
        "taxonomy_id",
        str(master.get("taxonomy_id") or release.get("master_taxonomy_id") or release.get("master_taxonomy_release_id") or ""),
    )
    enriched.setdefault("taxonomy_version", str(master.get("taxonomy_version") or release.get("master_taxonomy_version") or "unversioned"))
    enriched.setdefault("taxonomy_fingerprint", str(release.get("master_taxonomy_release_id") or ""))


def _merge_taxonomy_core_sections(enriched: dict[str, Any]) -> None:
    core = enriched.get("taxonomy_core")
    if not isinstance(core, Mapping):
        return
    for section in TAXONOMY_CODE_SECTIONS:
        values = core.get(section)
        if isinstance(values, list) and section not in enriched:
            enriched[section] = deepcopy(values)
    fallback_codes = core.get("fallback_codes")
    if isinstance(fallback_codes, Mapping) and "fallback_codes" not in enriched:
        enriched["fallback_codes"] = sorted(str(value) for value in fallback_codes.values() if str(value))
    promotion_slots = core.get("promotion_slots")
    if isinstance(promotion_slots, list) and "promotion_slots" not in enriched:
        enriched["promotion_slots"] = deepcopy(promotion_slots)
