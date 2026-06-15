"""Section-assignment helpers for owner-provided surface bundles."""
from __future__ import annotations

from typing import Any

from .. import policy
from .operation_models import operation_surfaces
from .types import DraftState, ModuleSurfaceBundle, SurfaceModel

_SECTION_NAMES = {name for name, _label in policy.SECTION_ORDER}
_KIND_FALLBACKS = {
    "settings": "Settings",
    "policy": "Settings",
    "ruleset": "Prompts/Assets",
    "capability_summary": "Operations",
}


def grouped_surface_models(bundle: ModuleSurfaceBundle, drafts: dict[str, DraftState]) -> dict[str, tuple[SurfaceModel, ...]]:
    grouped = {name: [] for name in _SECTION_NAMES if name != "Summary"}
    for surface in bundle.surfaces:
        if section_name_for_surface(surface) in grouped:
            grouped[section_name_for_surface(surface)].append(merge_surface(surface, drafts.get(surface.surface_id)))
    grouped["Operations"].extend(operation_surfaces(bundle))
    return {name: tuple(surfaces) for name, surfaces in grouped.items()}


def merge_surface(surface: SurfaceModel, draft: DraftState | None) -> SurfaceModel:
    if draft is None or surface.load_error:
        return surface
    return SurfaceModel(
        surface_id=surface.surface_id,
        label=surface.label,
        kind=surface.kind,
        editable=surface.editable,
        editor_kind=surface.editor_kind,
        descriptor=surface.descriptor,
        value=surface.value,
        draft=draft.value,
        operation_links=surface.operation_links,
        dirty=draft.dirty,
        message=draft.message,
        load_error=surface.load_error,
    )


def preview_models(bundle: ModuleSurfaceBundle, drafts: dict[str, DraftState], *, diff_text) -> tuple[SurfaceModel, ...]:
    preview = []
    for surface in bundle.surfaces:
        merged = merge_surface(surface, drafts.get(surface.surface_id))
        if merged.load_error:
            preview.append(merged)
            continue
        preview.append(
            SurfaceModel(
                surface_id=merged.surface_id,
                label=merged.label,
                kind=merged.kind,
                editable=False,
                editor_kind=_preview_editor_kind(merged),
                descriptor=merged.descriptor,
                value=_preview_payload(merged, diff_text(merged.value, merged.draft)),
                draft={},
                operation_links=(),
                dirty=merged.dirty,
                message=merged.message,
            )
        )
    return tuple(preview)


def section_name_for_surface(surface: SurfaceModel) -> str:
    return section_name_for_descriptor(surface.descriptor, kind=surface.kind)


def section_name_for_descriptor(descriptor: dict[str, Any], *, kind: str) -> str:
    explicit = str(descriptor.get("section") or "").strip()
    if explicit in _SECTION_NAMES:
        return explicit
    return _KIND_FALLBACKS.get(kind, "")


def _preview_payload(surface: SurfaceModel, diff: str) -> dict[str, Any]:
    payload = {"descriptor": surface.descriptor, "diff": diff}
    if surface.editor_kind == "taxonomy_release_draft":
        payload["current_summary"] = _taxonomy_release_summary(surface.value)
        payload["draft_summary"] = _taxonomy_release_summary(surface.draft)
        return payload
    payload["current"] = surface.value
    payload["draft"] = surface.draft
    return payload


def _taxonomy_release_summary(payload: dict[str, Any]) -> dict[str, Any]:
    release = payload.get("release") if isinstance(payload.get("release"), dict) else {}
    verification = payload.get("verification") if isinstance(payload.get("verification"), dict) else {}
    projections = release.get("projections") if isinstance(release.get("projections"), list) else []
    return {
        "artifact_root": str(payload.get("artifact_root") or ""),
        "release_id": str(release.get("release_id") or ""),
        "release_version": str(release.get("release_version") or ""),
        "projection_count": len(projections),
        "verification_status": str(verification.get("status") or ""),
    }


def _preview_editor_kind(surface: SurfaceModel) -> str:
    if surface.editor_kind == "taxonomy_release_draft":
        return "preview_result"
    return "preview"
