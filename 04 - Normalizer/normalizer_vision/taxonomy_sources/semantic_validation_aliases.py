from __future__ import annotations

from typing import Any

from ..taxonomy.types import normalize_lookup_token


def validate_alias_collisions(section_name: str, payload: dict[str, Any], *, locale: str) -> None:
    seen: dict[str, str] = {}
    for item_key, entry in payload.items():
        values = [item_key, str(entry.get("label") or ""), *list(entry.get("aliases") or [])]
        for raw_value in values:
            token = normalize_lookup_token(str(raw_value or ""))
            owner = seen.get(token)
            if owner is not None and owner != item_key:
                raise ValueError(f"master.text.{locale}.{section_name} enthaelt Alias-Kollisionen: {owner}, {item_key}")
            seen[token] = item_key
