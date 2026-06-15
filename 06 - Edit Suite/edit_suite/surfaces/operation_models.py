"""Synthetic operation surfaces derived from owner action metadata."""
from __future__ import annotations

from typing import Any

from .types import SurfaceModel


def operation_surfaces(bundle) -> tuple[SurfaceModel, ...]:
    surfaces = []
    for surface in bundle.surfaces:
        for action_link in _action_links(surface.descriptor):
            surfaces.append(
                SurfaceModel(
                    surface_id=_operation_surface_id(surface.surface_id, action_link),
                    label=str(action_link.get("label") or action_link.get("action") or "Action"),
                    kind="operation",
                    editable=False,
                    editor_kind="operation",
                    descriptor=_operation_descriptor(surface, action_link),
                    value=_operation_value(surface, action_link),
                    draft=_operation_value(surface, action_link),
                    operation_links=(action_link,),
                )
            )
    return tuple(surfaces)


def operation_preview_models(operation_results: dict[str, dict]) -> tuple[SurfaceModel, ...]:
    preview = []
    for surface_id, state in operation_results.items():
        response = state.get("response") if isinstance(state, dict) else None
        if not isinstance(response, dict):
            continue
        is_review = isinstance(response.get("review_payload"), dict)
        preview.append(
            SurfaceModel(
                surface_id=f"{surface_id}::preview",
                label=str(state.get("label") or surface_id),
                kind="operation_result",
                editable=False,
                editor_kind="review_result" if is_review else "preview_result",
                descriptor={"source_path": str(state.get("contract_module") or ""), "editable": False, "preview": ["summary", "review" if is_review else "workflow_preview"]},
                value={"result": response},
                draft={},
                operation_links=(),
                message=str(response.get("headline") or response.get("reason") or response.get("message") or ""),
            )
        )
    return tuple(preview)


def _operation_surface_id(surface_id: str, action_link: dict[str, Any]) -> str:
    return f"{surface_id}::action::{str(action_link.get('action') or 'run')}"


def _operation_descriptor(surface, action_link: dict[str, Any]) -> dict[str, Any]:
    return {
        "module_key": surface.descriptor.get("module_key"),
        "surface_id": _operation_surface_id(surface.surface_id, action_link),
        "kind": "operation",
        "source_path": str(surface.descriptor.get("source_path") or surface.surface_id),
        "editable": False,
        "preview": ["summary", "json"],
        "section": "Operations",
        "action_buttons": [dict(action_link)],
        "operation_owner_surface_id": surface.surface_id,
        "operation_summary": str(action_link.get("summary") or action_link.get("description") or ""),
    }


def _operation_value(surface, action_link: dict[str, Any]) -> dict[str, Any]:
    return {
        "owner_surface_id": surface.surface_id,
        "owner_label": surface.label,
        "summary": str(action_link.get("summary") or action_link.get("description") or ""),
        "workflow_stage": str(action_link.get("workflow_stage") or ""),
        "workflow_order": action_link.get("workflow_order"),
        "compile_effect": str(action_link.get("compile_effect") or ""),
        "prompt_effect": str(action_link.get("prompt_effect") or ""),
        "corpus_effect": str(action_link.get("corpus_effect") or ""),
        "validation_risks": list(action_link.get("validation_risks") or []),
        "inputs": list(action_link.get("inputs") or []),
    }


def _action_links(descriptor: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    buttons = descriptor.get("action_buttons")
    if not isinstance(buttons, list):
        return ()
    return tuple(item for item in buttons if isinstance(item, dict) and str(item.get("action") or "").strip())
