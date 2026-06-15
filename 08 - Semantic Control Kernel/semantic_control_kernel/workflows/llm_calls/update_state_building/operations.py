from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

_PROMOTION_RULE_KEYS = ("promotion_rules", "add_promotion_rules", "set_promotion_rules")


def _promote_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    promoted = deepcopy(dict(projection))
    _normalize_domain_marker_entries(promoted)
    _normalize_promotion_rule_entries(promoted)
    promoted["status"] = "active"
    promoted.setdefault(
        "kernel_policy",
        {
            "materialization_profile": "custom_projection.v1",
            "projection_family": "custom",
            "compatibility_profile": "normalizer_current",
        },
    )
    return promoted


def _normalize_promotion_rule_entries(value: dict[str, Any]) -> None:
    for key in _PROMOTION_RULE_KEYS:
        rules = value.get(key)
        if not isinstance(rules, list):
            continue
        compacted: list[Any] = []
        for rule in rules:
            if not isinstance(rule, Mapping):
                compacted.append(rule)
                continue
            source_paths = rule.get("source_paths")
            if not isinstance(source_paths, list):
                compacted.append(rule)
                continue
            normalized_paths = [path for item in source_paths if (path := str(item or "").strip())]
            if not normalized_paths:
                continue
            normalized_rule = dict(rule)
            normalized_rule["source_paths"] = normalized_paths
            compacted.append(normalized_rule)
        value[key] = compacted


def _normalize_domain_marker_entries(value: dict[str, Any]) -> None:
    routing_lexicon = value.get("routing_lexicon")
    if isinstance(routing_lexicon, dict):
        routing_lexicon["domain_markers"] = _domain_marker_mapping(routing_lexicon.get("domain_markers"))
    set_routing_lexicon = value.get("set_routing_lexicon")
    if isinstance(set_routing_lexicon, dict):
        set_routing_lexicon["domain_markers"] = _domain_marker_mapping(set_routing_lexicon.get("domain_markers"))
    for key in ("add_domain_markers", "remove_domain_markers"):
        if key in value:
            value[key] = _domain_marker_mapping(value.get(key))


def _domain_marker_mapping(value: Any) -> dict[str, list[str]]:
    if isinstance(value, Mapping):
        return {
            str(domain_id): [str(marker) for marker in markers]
            for domain_id, markers in value.items()
            if isinstance(markers, list)
        }
    if isinstance(value, list):
        result: dict[str, list[str]] = {}
        for item in value:
            if not isinstance(item, Mapping) or not isinstance(item.get("domain_id"), str):
                continue
            markers = item.get("markers", [])
            result[str(item["domain_id"])] = [str(marker) for marker in markers] if isinstance(markers, list) else []
        return result
    return {}
