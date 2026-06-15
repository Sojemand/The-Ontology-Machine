from __future__ import annotations

from typing import Any, Mapping


def validate_projection_binding_payload(
    *,
    taxonomy_ref: Mapping[str, Any],
    projection_refs: list[Mapping[str, Any]],
) -> tuple[bool, list[str], list[str]]:
    taxonomy_codes = set(str(item) for item in (taxonomy_ref.get("codes") or taxonomy_ref.get("allowed_codes") or ()) if str(item))
    errors: list[str] = []
    warnings: list[str] = []
    for projection in projection_refs:
        for code in projection.get("included_taxonomy_codes", ()):
            if taxonomy_codes and str(code) not in taxonomy_codes:
                errors.append(f"unknown_taxonomy_code:{code}")
    if not taxonomy_codes:
        warnings.append("taxonomy_codes_missing")
    return not errors, errors, warnings
