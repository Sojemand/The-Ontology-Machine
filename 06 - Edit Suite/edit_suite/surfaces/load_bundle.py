"""Contract loading workflow for owner-provided surfaces."""
from __future__ import annotations

from typing import Any

from ..registry.types import ModuleReadinessEntry
from .contract_client import invoke_contract
from .types import DraftState, ModuleSurfaceBundle, SummaryCardModel, SurfaceModel


def load_bundle(entry: ModuleReadinessEntry, *, state_root) -> ModuleSurfaceBundle:
    response = _read_bundle_response(entry, state_root)
    descriptors = tuple(_require_mapping(item, label="surface_descriptor") for item in response.get("surfaces", ()))
    surfaces = tuple(_surface_model(entry, state_root, descriptor) for descriptor in descriptors)
    return ModuleSurfaceBundle(
        source="contract",
        surfaces=surfaces,
        module_summary=str(response.get("module_summary") or ""),
        summary_cards=_summary_cards(response),
    )


def validate_draft(entry: ModuleReadinessEntry, draft: DraftState, *, state_root) -> DraftState:
    response = invoke_contract(entry, state_root, {"action": "validate_surface", "surface_id": draft.surface_id, "value": draft.value})
    _require_ok(response)
    return DraftState(surface_id=draft.surface_id, value=_require_mapping(response.get("value"), label=draft.surface_id), dirty=draft.dirty, message="Validation OK")


def write_draft(entry: ModuleReadinessEntry, draft: DraftState, *, state_root) -> DraftState:
    response = invoke_contract(entry, state_root, {"action": "write_surface", "surface_id": draft.surface_id, "value": draft.value})
    _require_ok(response)
    value = _require_mapping(response.get("value"), label=draft.surface_id)
    return DraftState(surface_id=draft.surface_id, value=value, dirty=False, message="Saved")


def _read_bundle_response(entry: ModuleReadinessEntry, state_root) -> dict[str, Any]:
    try:
        response = invoke_contract(entry, state_root, {"action": "read_bundle"})
    except Exception as exc:
        if not _is_unknown_action_exception(exc):
            raise
        return _legacy_bundle_response(entry, state_root)
    if _is_unknown_action_response(response):
        return _legacy_bundle_response(entry, state_root)
    _require_ok(response)
    if not isinstance(response.get("surfaces"), list):
        if "value" in response:
            return _legacy_bundle_response(entry, state_root)
        raise ValueError("read_bundle must return a surface list.")
    return response


def _legacy_bundle_response(entry: ModuleReadinessEntry, state_root) -> dict[str, Any]:
    response = invoke_contract(entry, state_root, {"action": "describe_surfaces"})
    _require_ok(response)
    descriptors = tuple(_require_mapping(item, label="surface_descriptor") for item in response.get("surfaces", ()))
    response["surfaces"] = [_legacy_surface_payload(entry, state_root, descriptor) for descriptor in descriptors]
    return response


def _surface_model(entry: ModuleReadinessEntry, state_root, descriptor: dict[str, Any]) -> SurfaceModel:
    if descriptor.get("load_error"):
        return _error_surface_model(descriptor, str(descriptor.get("load_error") or "Contract error"))
    if isinstance(descriptor.get("value"), dict):
        return _value_surface_model(descriptor, _require_mapping(descriptor.get("value"), label=str(descriptor.get("surface_id") or "")))
    return _read_surface_model(entry, state_root, descriptor)


def _read_surface_model(entry: ModuleReadinessEntry, state_root, descriptor: dict[str, Any]) -> SurfaceModel:
    surface_id = str(descriptor.get("surface_id") or "")
    try:
        value_response = invoke_contract(entry, state_root, {"action": "read_surface", "surface_id": surface_id})
        _require_ok(value_response)
        value = _require_mapping(value_response.get("value"), label=surface_id)
    except Exception as exc:
        return _error_surface_model(descriptor, str(exc))
    return _value_surface_model(descriptor, value)


def _legacy_surface_payload(entry: ModuleReadinessEntry, state_root, descriptor: dict[str, Any]) -> dict[str, Any]:
    item = dict(descriptor)
    surface = _read_surface_model(entry, state_root, descriptor)
    if surface.load_error:
        item["load_error"] = surface.load_error
    else:
        item["value"] = surface.value
    return item


def _value_surface_model(descriptor: dict[str, Any], value: dict[str, Any]) -> SurfaceModel:
    surface_id = str(descriptor.get("surface_id") or "")
    return SurfaceModel(
        surface_id=surface_id,
        label=str(descriptor.get("label") or surface_id),
        kind=str(descriptor.get("kind") or ""),
        editable=bool(descriptor.get("editable")),
        editor_kind=_editor_kind(descriptor),
        descriptor=descriptor,
        value=value,
        draft=value,
        operation_links=tuple(value.get("operation_links", descriptor.get("operation_links", []))),
    )


def _error_surface_model(descriptor: dict[str, Any], error: str) -> SurfaceModel:
    surface_id = str(descriptor.get("surface_id") or "")
    payload = {
        "surface_id": surface_id,
        "source_path": str(descriptor.get("source_path") or ""),
        "error": error,
        "descriptor": descriptor,
    }
    return SurfaceModel(
        surface_id=surface_id,
        label=str(descriptor.get("label") or surface_id),
        kind=str(descriptor.get("kind") or "contract_error"),
        editable=False,
        editor_kind="readonly",
        descriptor=descriptor,
        value=payload,
        draft=payload,
        operation_links=tuple(descriptor.get("operation_links", [])),
        message=f"Error: {error}",
        load_error=error,
    )


def _editor_kind(descriptor: dict[str, Any]) -> str:
    explicit = str(descriptor.get("editor_kind") or "").strip()
    if explicit:
        return explicit
    kind = str(descriptor.get("kind") or "")
    storage_kind = str(descriptor.get("storage_kind") or "")
    field_groups = descriptor.get("field_groups")
    if storage_kind == "env_file":
        return "form"
    if bool(descriptor.get("editable")) and isinstance(field_groups, list) and field_groups:
        return "form"
    if kind == "settings":
        return "form"
    if kind == "prompt_bundle":
        return "prompt_bundle"
    if kind == "capability_summary":
        return "readonly"
    return "json"


def _require_mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must return a JSON object.")
    return value


def _require_ok(response: dict) -> None:
    if str(response.get("status") or "") != "ok":
        raise ValueError(str(response.get("reason") or response.get("message") or "Contract error"))


def _is_unknown_action_response(response: dict[str, Any]) -> bool:
    if str(response.get("status") or "") == "ok":
        return False
    reason = str(response.get("reason") or response.get("message") or "").strip().casefold()
    return reason in {"unknown action", "unbekannte aktion", "unsupported action"}


def _is_unknown_action_exception(exc: Exception) -> bool:
    if isinstance(exc, KeyError) and exc.args == ("surface_id",):
        return True
    text = str(exc).strip().casefold()
    return text in {"unknown action", "unbekannte aktion", "unsupported action"}


def _summary_cards(response: dict[str, Any]) -> tuple[SummaryCardModel, ...]:
    items = response.get("summary_cards")
    if not isinstance(items, list):
        return ()
    cards = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        lines = item.get("lines")
        cards.append(
            SummaryCardModel(
                card_id=str(item.get("card_id") or f"summary_card_{index}"),
                label=str(item.get("label") or f"Summary {index + 1}"),
                body=str(item.get("body") or ""),
                lines=tuple(str(line) for line in lines if isinstance(line, (str, int, float, bool))) if isinstance(lines, list) else (),
            )
        )
    return tuple(cards)
