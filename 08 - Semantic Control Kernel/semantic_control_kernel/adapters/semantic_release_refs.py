from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import stable_hash


def taxonomy_ref_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("taxonomy_ref"), Mapping):
        return dict(payload["taxonomy_ref"])
    staged = payload.get("staged_taxonomy_ref")
    if isinstance(staged, Mapping) and isinstance(staged.get("component_identity"), Mapping):
        return dict(staged["component_identity"])
    return {}


def projection_refs_from_payload(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("projection_refs"), list):
        return [dict(item) for item in payload["projection_refs"] if isinstance(item, Mapping)]
    if isinstance(payload.get("custom_projection"), Mapping):
        custom = payload["custom_projection"]
        if isinstance(custom.get("projection_refs"), list):
            return [dict(item) for item in custom["projection_refs"] if isinstance(item, Mapping)]
        component = custom.get("component_identity")
        if isinstance(component, Mapping):
            return projection_refs_from_identity(component)
        if custom.get("projection_id"):
            return [dict(custom)]
    staged = payload.get("staged_projection_ref")
    if isinstance(staged, Mapping) and isinstance(staged.get("component_identity"), Mapping):
        return projection_refs_from_identity(staged["component_identity"])
    component = payload.get("component_identity")
    if isinstance(component, Mapping):
        return projection_refs_from_identity(component)
    return []


def projection_refs_from_identity(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    if isinstance(value.get("projection_refs"), list):
        return [dict(item) for item in value["projection_refs"] if isinstance(item, Mapping)]
    if value.get("projection_id") or value.get("projection_ids"):
        return [dict(value)]
    return []


def requires_detached_custom_release_write(payload: Mapping[str, Any], release_ref: Mapping[str, Any]) -> bool:
    has_custom_source = bool(
        payload.get("base_release_path")
        or payload.get("projection_update_state")
        or payload.get("semantic_merge_package")
        or payload.get("merge_context")
    )
    return bool(
        release_ref.get("release_id")
        and isinstance(release_ref.get("taxonomy_ref"), Mapping)
        and isinstance(release_ref.get("projection_refs"), list)
        and has_custom_source
    )


def projection_refs_from_update_state(update_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    precursors = [item for item in update_state.get("projection_precursors", ()) if isinstance(item, Mapping)]
    if not precursors and isinstance(update_state.get("projection_ids"), list):
        precursors = [{"projection_id": item} for item in update_state["projection_ids"] if str(item)]
    refs: list[dict[str, Any]] = []
    for precursor in precursors:
        projection_id = str(precursor.get("projection_id") or "")
        if not projection_id:
            continue
        refs.append(
            {
                "projection_id": projection_id,
                "projection_fingerprint": stable_hash(f"projection:{projection_id}:{repr(sorted(dict(precursor).items()))}"),
                "included_taxonomy_codes": included_taxonomy_codes(precursor),
            }
        )
    return refs


def included_taxonomy_codes(precursor: Mapping[str, Any]) -> list[str]:
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
    return list(dict.fromkeys(codes))


def artifact_root_from_semantic_release_folder(semantic_release_folder: str) -> str:
    if not semantic_release_folder:
        return ""
    return str(Path(semantic_release_folder).resolve(strict=False).parent)


_taxonomy_ref_from_payload = taxonomy_ref_from_payload
_projection_refs_from_payload = projection_refs_from_payload
_projection_refs_from_identity = projection_refs_from_identity
_requires_detached_custom_release_write = requires_detached_custom_release_write
_projection_refs_from_update_state = projection_refs_from_update_state
_included_taxonomy_codes = included_taxonomy_codes
_artifact_root_from_semantic_release_folder = artifact_root_from_semantic_release_folder
