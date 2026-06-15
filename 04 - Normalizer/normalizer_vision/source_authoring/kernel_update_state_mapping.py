from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping

from ..semantic_release.kernel_candidate import stable_hash
from .control_language import control_locale_or_default


TAXONOMY_CODE_SECTIONS = (
    "domains",
    "document_types",
    "categories",
    "subcategories",
    "field_codes",
    "row_types",
    "cell_codes",
)
SEMANTIC_BINDING_CODE_SECTIONS = ("field_codes", "row_types", "cell_codes")


def extract_update_state(payload: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    return {}


def taxonomy_identity(update_state: Mapping[str, Any]) -> dict[str, Any]:
    taxonomy_id = str(
        update_state.get("taxonomy_id")
        or update_state.get("target_taxonomy_id")
        or update_state.get("taxonomy_core", {}).get("taxonomy_id")
        or f"taxonomy_{stable_hash(repr(sorted(dict(update_state).items())))[:12]}"
    )
    return {
        "taxonomy_id": taxonomy_id,
        "taxonomy_fingerprint": stable_hash(f"taxonomy:{repr(sorted(dict(update_state).items()))}"),
        "runtime_locale": control_locale_or_default(update_state.get("runtime_locale")),
        "codes": list(_taxonomy_codes(update_state)),
    }


def projection_identity(update_state: Mapping[str, Any], *, taxonomy_ref: Mapping[str, Any]) -> dict[str, Any]:
    projection_ids = list(
        str(item)
        for item in (
            update_state.get("projection_ids")
            or [item.get("projection_id") for item in update_state.get("projection_precursors", []) if isinstance(item, Mapping)]
            or [f"projection_{stable_hash(repr(sorted(dict(update_state).items())))[:12]}"]
        )
        if str(item)
    )
    fingerprints = {
        projection_id: stable_hash(f"projection:{projection_id}:{repr(sorted(dict(update_state).items()))}")
        for projection_id in projection_ids
    }
    return {
        "projection_ids": projection_ids,
        "projection_fingerprints": fingerprints,
        "included_taxonomy_codes": list(_taxonomy_codes(update_state) or taxonomy_ref.get("codes", [])),
    }


def _taxonomy_codes(update_state: Mapping[str, Any]) -> tuple[str, ...]:
    codes: list[str] = []
    core = update_state.get("taxonomy_core")
    if isinstance(core, Mapping):
        _append_codes(codes, core.get("codes", ()))
        for section in TAXONOMY_CODE_SECTIONS:
            _append_codes(codes, core.get(section, ()))
    semantic_binding = update_state.get("semantic_binding")
    if isinstance(semantic_binding, Mapping):
        _append_codes(codes, semantic_binding.get("codes", ()))
        for section in SEMANTIC_BINDING_CODE_SECTIONS:
            _append_codes(codes, semantic_binding.get(section, ()))
    for precursor in update_state.get("projection_precursors", ()):
        if isinstance(precursor, Mapping):
            codes.extend(_projection_codes(precursor))
    return tuple(dict.fromkeys(codes))


def _append_codes(codes: list[str], values: Any) -> None:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return
    for item in values:
        code = _item_code(item)
        if code:
            codes.append(code)


def _item_code(item: Any) -> str:
    if isinstance(item, Mapping):
        value = item.get("code") or item.get("id")
    else:
        value = item
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ""


def _projection_codes(precursor: Mapping[str, Any]) -> list[str]:
    codes: list[str] = []
    for key in (
        "domain_ids",
        "include_document_types",
        "include_categories",
        "include_subcategories",
        "include_field_codes",
        "include_row_types",
        "include_cell_codes",
    ):
        value = precursor.get(key)
        if isinstance(value, list):
            codes.extend(str(item) for item in value if str(item))
    return codes
