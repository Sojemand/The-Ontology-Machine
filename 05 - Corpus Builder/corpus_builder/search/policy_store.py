"""Search-policy file loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_TOP_LEVEL_KEYS = ("fulltext", "semantic", "hybrid", "readonly", "fts")


def search_policy_path(module_root: str | Path) -> Path:
    return Path(module_root).resolve() / "config" / "search_policy.json"


def default_search_policy_payload() -> dict[str, Any]:
    return {
        "fulltext": {"limit_default": 20},
        "semantic": {"top_k_default": 10},
        "hybrid": {
            "top_k_default": 10,
            "candidate_multiplier": 2,
            "fts_weight": 0.6,
            "vec_weight": 0.4,
        },
        "readonly": {"max_rows": 100},
        "fts": {"normalize_by_max_score": True},
    }


def load_search_policy(module_root: str | Path) -> dict[str, Any]:
    path = search_policy_path(module_root)
    if not path.exists():
        raise ValueError(f"Search Policy fehlt: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("config/search_policy.json muss ein JSON-Objekt sein.")
    return validate_search_policy_payload(payload)


def validate_search_policy_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload = _mapping(data, label="search_policy")
    _require_exact_keys(payload, _TOP_LEVEL_KEYS, label="search_policy")
    fulltext = _mapping(payload.get("fulltext"), label="search_policy.fulltext")
    semantic = _mapping(payload.get("semantic"), label="search_policy.semantic")
    hybrid = _mapping(payload.get("hybrid"), label="search_policy.hybrid")
    readonly = _mapping(payload.get("readonly"), label="search_policy.readonly")
    fts = _mapping(payload.get("fts"), label="search_policy.fts")
    _require_exact_keys(fulltext, ("limit_default",), label="search_policy.fulltext")
    _require_exact_keys(semantic, ("top_k_default",), label="search_policy.semantic")
    _require_exact_keys(
        hybrid,
        ("top_k_default", "candidate_multiplier", "fts_weight", "vec_weight"),
        label="search_policy.hybrid",
    )
    _require_exact_keys(readonly, ("max_rows",), label="search_policy.readonly")
    _require_exact_keys(fts, ("normalize_by_max_score",), label="search_policy.fts")
    fts_weight = _required_fraction(hybrid.get("fts_weight"), field_name="search_policy.hybrid.fts_weight")
    vec_weight = _required_fraction(hybrid.get("vec_weight"), field_name="search_policy.hybrid.vec_weight")
    if abs((fts_weight + vec_weight) - 1.0) > 1e-9:
        raise ValueError("search_policy.hybrid.fts_weight und vec_weight muessen zusammen 1.0 ergeben.")
    return {
        "fulltext": {
            "limit_default": _required_positive_int(
                fulltext.get("limit_default"),
                field_name="search_policy.fulltext.limit_default",
            )
        },
        "semantic": {
            "top_k_default": _required_positive_int(
                semantic.get("top_k_default"),
                field_name="search_policy.semantic.top_k_default",
            )
        },
        "hybrid": {
            "top_k_default": _required_positive_int(
                hybrid.get("top_k_default"),
                field_name="search_policy.hybrid.top_k_default",
            ),
            "candidate_multiplier": _required_positive_int(
                hybrid.get("candidate_multiplier"),
                field_name="search_policy.hybrid.candidate_multiplier",
            ),
            "fts_weight": fts_weight,
            "vec_weight": vec_weight,
        },
        "readonly": {
            "max_rows": _required_positive_int(
                readonly.get("max_rows"),
                field_name="search_policy.readonly.max_rows",
            )
        },
        "fts": {
            "normalize_by_max_score": _required_bool(
                fts.get("normalize_by_max_score"),
                field_name="search_policy.fts.normalize_by_max_score",
            )
        },
    }


def fulltext_limit_default(policy: dict[str, Any]) -> int:
    return int(policy["fulltext"]["limit_default"])


def semantic_top_k_default(policy: dict[str, Any]) -> int:
    return int(policy["semantic"]["top_k_default"])


def hybrid_top_k_default(policy: dict[str, Any]) -> int:
    return int(policy["hybrid"]["top_k_default"])


def hybrid_candidate_multiplier(policy: dict[str, Any]) -> int:
    return int(policy["hybrid"]["candidate_multiplier"])


def hybrid_weights(policy: dict[str, Any]) -> tuple[float, float]:
    return float(policy["hybrid"]["fts_weight"]), float(policy["hybrid"]["vec_weight"])


def readonly_max_rows(policy: dict[str, Any]) -> int:
    return int(policy["readonly"]["max_rows"])


def normalize_fts_by_max_score(policy: dict[str, Any]) -> bool:
    return bool(policy["fts"]["normalize_by_max_score"])


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


def _required_bool(value: object, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} muss true oder false sein.")
    return value


def _required_positive_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} muss eine positive Ganzzahl sein.")
    return value


def _required_fraction(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} muss eine Zahl zwischen 0.0 und 1.0 sein.")
    normalized = float(value)
    if normalized < 0.0 or normalized > 1.0:
        raise ValueError(f"{field_name} muss eine Zahl zwischen 0.0 und 1.0 sein.")
    return normalized
