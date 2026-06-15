from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .kernel_candidate import stable_hash
from .kernel_merge_common import first_text, merged_text_list

TAXONOMY_SECTIONS = (
    "domains",
    "document_types",
    "categories",
    "subcategories",
    "field_codes",
    "row_types",
    "cell_codes",
    "promotion_slots",
)


def merge_taxonomy_refs(taxonomy_refs: Sequence[Mapping[str, Any]], *, merge_run_id: str) -> dict[str, Any]:
    refs = _dedupe_taxonomy_refs(taxonomy_refs)
    if not refs:
        return {}
    if len(refs) == 1:
        return refs[0]
    seed = stable_hash(repr(refs))
    merged: dict[str, Any] = {
        "source": "merged",
        "taxonomy_fingerprint": stable_hash(f"taxonomy:{merge_run_id}:{seed}"),
        "taxonomy_id": f"merged.taxonomy.{seed[:12]}",
        "taxonomy_version": "merged.v1",
    }
    runtime_locale = first_text(refs, "runtime_locale")
    if runtime_locale:
        merged["runtime_locale"] = runtime_locale
    master = _merge_master_taxonomies(refs, merged)
    if master:
        merged["master_taxonomy"] = master
        for section in TAXONOMY_SECTIONS:
            if isinstance(master.get(section), list):
                merged[section] = deepcopy(master[section])
    _merge_taxonomy_lists(merged, refs)
    _merge_term_summaries(merged, refs)
    return merged


def _dedupe_taxonomy_refs(taxonomy_refs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in taxonomy_refs:
        if not item:
            continue
        key = (str(item.get("taxonomy_id") or ""), str(item.get("taxonomy_fingerprint") or ""))
        if key in seen:
            continue
        seen.add(key)
        refs.append(deepcopy(dict(item)))
    return refs


def _merge_taxonomy_lists(merged: dict[str, Any], refs: Sequence[Mapping[str, Any]]) -> None:
    allowed_codes = merged_text_list(refs, "allowed_codes")
    if allowed_codes:
        merged["allowed_codes"] = allowed_codes
    fallback_codes = merged_text_list(refs, "fallback_codes")
    if fallback_codes:
        merged["fallback_codes"] = fallback_codes


def _merge_term_summaries(merged: dict[str, Any], refs: Sequence[Mapping[str, Any]]) -> None:
    term_summaries: dict[str, Any] = {}
    for ref in refs:
        values = ref.get("term_summaries")
        if isinstance(values, Mapping):
            term_summaries.update(deepcopy(dict(values)))
    if term_summaries:
        merged["term_summaries"] = term_summaries


def _merge_master_taxonomies(refs: Sequence[Mapping[str, Any]], identity: Mapping[str, Any]) -> dict[str, Any]:
    masters = [
        dict(item.get("master_taxonomy") or item.get("taxonomy_core") or {})
        for item in refs
        if isinstance(item.get("master_taxonomy") or item.get("taxonomy_core"), Mapping)
    ]
    if not masters:
        return {}
    merged = deepcopy(masters[0])
    merged["taxonomy_id"] = identity["taxonomy_id"]
    merged["taxonomy_version"] = identity["taxonomy_version"]
    for section in TAXONOMY_SECTIONS:
        merged_section: list[dict[str, Any]] = []
        seen_codes: set[str] = set()
        for master in masters:
            values = master.get(section)
            if not isinstance(values, list):
                continue
            for item in values:
                if not isinstance(item, Mapping):
                    continue
                code = _taxonomy_section_item_key(section, item)
                if not code or code in seen_codes:
                    continue
                seen_codes.add(code)
                merged_section.append(deepcopy(dict(item)))
        if merged_section:
            merged[section] = merged_section
    return merged


def _taxonomy_section_item_key(section: str, item: Mapping[str, Any]) -> str:
    if section == "promotion_slots":
        return str(item.get("slot") or "").strip()
    return str(item.get("code") or "").strip()
