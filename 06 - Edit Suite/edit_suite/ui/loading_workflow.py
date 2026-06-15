"""Cached-first registry and bundle loading for the Edit Suite UI."""

from __future__ import annotations

from datetime import datetime, timezone

from ..registry import RegistrySnapshot, discover_registry
from ..repository import load_bundle_cache, load_registry_cache, save_bundle_cache
from ..surfaces import ModuleSurfaceBundle, SurfaceModel, load_bundle
from .loading_state import failed_slots
from . import background_jobs, view_model


def initial_snapshot(state_root) -> RegistrySnapshot:
    cached = load_registry_cache(state_root)
    if not isinstance(cached, dict):
        return RegistrySnapshot(
            generated_at=datetime.now(timezone.utc).isoformat(),
            source="loading",
            stale=False,
            message="Loading registry...",
            entries=(),
        )
    snapshot = RegistrySnapshot.from_dict(cached)
    return RegistrySnapshot(
        generated_at=snapshot.generated_at,
        source="cache",
        stale=False,
        message="Refreshing registry...",
        entries=snapshot.entries,
    )


def refresh_registry(app) -> None:
    failed_slots(app).clear()
    app._registry_loading = True
    token = background_jobs.next_token(app, "registry")
    _rerender(app)
    background_jobs.start(
        app,
        work=lambda: discover_registry(app._pipeline_root, state_root=app._state_root),
        deliver=lambda result, error: _apply_registry(app, token, result, error),
    )


def ensure_bundle(app, entry, *, force: bool = False, rerender: bool = False) -> None:
    if entry.readiness != "ready":
        return
    slot_name = entry.slot_name
    if not force and slot_name not in app._bundles:
        cached = _cached_bundle(app, entry)
        if cached is not None:
            app._bundles[slot_name] = cached
            app._bundle_errors.pop(slot_name, None)
    if force:
        app._bundle_live_slots.discard(slot_name)
        app._bundle_errors.pop(slot_name, None)
        failed_slots(app).discard(slot_name)
    if slot_name in app._bundle_loading or slot_name in app._bundle_live_slots or slot_name in failed_slots(app):
        return
    app._bundle_loading.add(slot_name)
    token = background_jobs.next_token(app, f"bundle:{slot_name}")
    if rerender:
        _rerender(app, detail_only=True)
    background_jobs.start(
        app,
        work=lambda: load_bundle(entry, state_root=app._state_root),
        deliver=lambda result, error: _apply_bundle(app, entry, token, result, error),
    )


def remember_saved_draft(app, entry, draft) -> None:
    bundle = app._bundles.get(entry.slot_name)
    if bundle is None or not isinstance(getattr(bundle, "surfaces", None), tuple):
        return
    surfaces = tuple(_replace_surface(surface, draft) for surface in bundle.surfaces)
    updated = ModuleSurfaceBundle(
        source=bundle.source,
        surfaces=surfaces,
        module_summary=bundle.module_summary,
        summary_cards=bundle.summary_cards,
    )
    app._bundles[entry.slot_name] = updated
    app._bundle_errors.pop(entry.slot_name, None)
    failed_slots(app).discard(entry.slot_name)
    save_bundle_cache(app._state_root, _bundle_cache_key(entry), updated.to_dict())


def loading_message(app, slot_name: str) -> str:
    return "Loading..." if slot_name in getattr(app, "_bundle_loading", set()) else ""


def status_text(app, entry) -> str:
    if entry.slot_name in getattr(app, "_bundle_loading", set()):
        return "Loading..."
    bundle_error = getattr(app, "_bundle_errors", {}).get(entry.slot_name, "")
    if bundle_error:
        prefix = "Error (cache)" if entry.slot_name in getattr(app, "_bundles", {}) else "Error"
        headline = str(bundle_error).splitlines()[0].strip()
        return f"{prefix}: {headline}" if headline else prefix
    return str(getattr(entry, "readiness", "ready") or "ready")


def entry_is_loading(app) -> bool:
    entry = app._selected_entry()
    return bool(entry and entry.slot_name in getattr(app, "_bundle_loading", set()))


def _apply_registry(app, token: int, snapshot, error: Exception | None) -> None:
    if not background_jobs.is_current(app, "registry", token):
        return
    app._registry_loading = False
    if error is None and snapshot is not None:
        app._snapshot = snapshot
        _trim_state(app)
        app._selected_module = view_model.preferred_module_key(app._snapshot, app._selected_module)
    elif not app._snapshot.entries:
        app._snapshot = RegistrySnapshot(
            generated_at=datetime.now(timezone.utc).isoformat(),
            source="error",
            stale=True,
            message=str(error),
            entries=(),
        )
    _rerender(app)


def _apply_bundle(app, entry, token: int, bundle, error: Exception | None) -> None:
    slot_name = entry.slot_name
    if not background_jobs.is_current(app, f"bundle:{slot_name}", token):
        return
    app._bundle_loading.discard(slot_name)
    if error is None and bundle is not None:
        app._bundle_live_slots.add(slot_name)
        failed_slots(app).discard(slot_name)
        app._bundles[slot_name] = bundle
        app._bundle_errors.pop(slot_name, None)
        save_bundle_cache(app._state_root, _bundle_cache_key(entry), bundle.to_dict())
    else:
        failed_slots(app).add(slot_name)
        app._bundle_errors[slot_name] = str(error)
    if app._selected_module == slot_name:
        _rerender(app, detail_only=True)


def _cached_bundle(app, entry) -> ModuleSurfaceBundle | None:
    payload = load_bundle_cache(app._state_root, _bundle_cache_key(entry))
    if not isinstance(payload, dict):
        return None
    cached = ModuleSurfaceBundle.from_dict(payload)
    return ModuleSurfaceBundle(
        source="cache",
        surfaces=cached.surfaces,
        module_summary=cached.module_summary,
        summary_cards=cached.summary_cards,
    )


def _bundle_cache_key(entry) -> str:
    return str(entry.module_key or entry.slot_name)


def _replace_surface(surface: SurfaceModel, draft) -> SurfaceModel:
    if surface.surface_id != draft.surface_id:
        return surface
    return SurfaceModel(
        surface_id=surface.surface_id,
        label=surface.label,
        kind=surface.kind,
        editable=surface.editable,
        editor_kind=surface.editor_kind,
        descriptor=surface.descriptor,
        value=draft.value,
        draft=draft.value,
        operation_links=surface.operation_links,
        dirty=False,
        message=draft.message,
        load_error="",
    )


def _trim_state(app) -> None:
    valid = {entry.slot_name for entry in app._snapshot.entries if entry.readiness == "ready"}
    app._bundles = {key: value for key, value in app._bundles.items() if key in valid}
    app._bundle_errors = {key: value for key, value in app._bundle_errors.items() if key in valid}
    app._drafts = {key: value for key, value in app._drafts.items() if key in valid}
    app._bundle_loading.intersection_update(valid)
    app._bundle_live_slots.intersection_update(valid)
    failed_slots(app).intersection_update(valid)


def _rerender(app, *, detail_only: bool = False) -> None:
    if not hasattr(app, "_render"):
        return
    app._render_detail_only = detail_only
    app._render()
