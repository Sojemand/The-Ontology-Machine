"""Owner-local read/write helpers for non-config edit surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import atomic_json_write
from ..search.policy_store import load_search_policy, search_policy_path, validate_search_policy_payload

_SEARCH_POLICY_FIELDS = (
    "fulltext.limit_default",
    "semantic.top_k_default",
    "hybrid.top_k_default",
    "hybrid.candidate_multiplier",
    "hybrid.fts_weight",
    "hybrid.vec_weight",
    "readonly.max_rows",
    "fts.normalize_by_max_score",
)


def read_search_policy(module_root: Path) -> dict[str, Any]:
    return _flatten_search_policy(load_search_policy(module_root))


def validate_search_policy_surface(data: dict[str, Any]) -> dict[str, Any]:
    return _flatten_search_policy(build_search_policy_payload(data))


def write_search_policy(module_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    atomic_json_write(search_policy_path(module_root), build_search_policy_payload(payload))
    return read_search_policy(module_root)


def read_debug_capabilities(module_root: Path) -> dict[str, Any]:
    manifest = json.loads((module_root / "module-manifest.json").read_text(encoding="utf-8"))
    operation_links = _operation_links(manifest)
    return {
        "module_key": str(manifest.get("module_key") or ""),
        "display_name": str(manifest.get("display_name") or ""),
        "contract_module": str(manifest.get("contract_module") or ""),
        "capabilities": dict(manifest.get("debug_surface") or {}),
        "actions": [link["action"] for link in operation_links],
        "operation_links": operation_links,
    }


def build_search_policy_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload = _mapping(data, label="corpus_builder.search_policy")
    _require_exact_keys(payload, _SEARCH_POLICY_FIELDS, label="corpus_builder.search_policy")
    return validate_search_policy_payload(
        {
            "fulltext": {"limit_default": payload["fulltext.limit_default"]},
            "semantic": {"top_k_default": payload["semantic.top_k_default"]},
            "hybrid": {
                "top_k_default": payload["hybrid.top_k_default"],
                "candidate_multiplier": payload["hybrid.candidate_multiplier"],
                "fts_weight": payload["hybrid.fts_weight"],
                "vec_weight": payload["hybrid.vec_weight"],
            },
            "readonly": {"max_rows": payload["readonly.max_rows"]},
            "fts": {"normalize_by_max_score": payload["fts.normalize_by_max_score"]},
        }
    )


def _flatten_search_policy(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "fulltext.limit_default": payload["fulltext"]["limit_default"],
        "semantic.top_k_default": payload["semantic"]["top_k_default"],
        "hybrid.top_k_default": payload["hybrid"]["top_k_default"],
        "hybrid.candidate_multiplier": payload["hybrid"]["candidate_multiplier"],
        "hybrid.fts_weight": payload["hybrid"]["fts_weight"],
        "hybrid.vec_weight": payload["hybrid"]["vec_weight"],
        "readonly.max_rows": payload["readonly"]["max_rows"],
        "fts.normalize_by_max_score": payload["fts"]["normalize_by_max_score"],
    }


def _operation_links(manifest: dict[str, Any]) -> list[dict[str, str]]:
    contract_module = str(manifest.get("contract_module") or "")
    actions = manifest.get("actions") or []
    return [
        {
            "action": action,
            "label": action.replace("_", " ").title(),
            "contract_module": contract_module,
        }
        for action in actions
        if isinstance(action, str) and action.strip()
    ]


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    return value


def _require_exact_keys(payload: dict[str, Any], expected: tuple[str, ...], *, label: str) -> None:
    unknown = sorted(set(payload) - set(expected))
    if unknown:
        raise ValueError(f"{label} enthaelt unbekannte Felder: {', '.join(unknown)}")
    missing = [field_name for field_name in expected if field_name not in payload]
    if missing:
        raise ValueError(f"{label} enthaelt fehlende Felder: {', '.join(missing)}")
