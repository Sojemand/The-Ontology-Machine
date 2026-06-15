from __future__ import annotations

from types import SimpleNamespace

from edit_suite.surfaces.types import ModuleSurfaceBundle, SurfaceModel
from edit_suite.ui import loading_workflow


def test_loading_workflow_ignores_stale_bundle_results(monkeypatch, tmp_path) -> None:
    entry = SimpleNamespace(slot_name="01 - Optimizer", module_key="optimizer")
    bundle = ModuleSurfaceBundle(source="contract", surfaces=(SurfaceModel("optimizer.settings", "Settings", "settings", True, "form", {}, {"parallel_workers": 2}, {"parallel_workers": 2}, ()),))
    app = SimpleNamespace(
        _selected_module=entry.slot_name,
        _request_tokens={f"bundle:{entry.slot_name}": 2},
        _bundle_loading={entry.slot_name},
        _bundle_live_slots=set(),
        _bundles={},
        _bundle_errors={},
        _drafts={},
        _state_root=tmp_path,
        _render=lambda: None,
        _render_detail_only=False,
    )
    monkeypatch.setattr(loading_workflow, "save_bundle_cache", lambda *_args, **_kwargs: None)

    loading_workflow._apply_bundle(app, entry, 1, bundle, None)
    assert app._bundles == {}

    loading_workflow._apply_bundle(app, entry, 2, bundle, None)
    assert app._bundles[entry.slot_name].surfaces[0].surface_id == "optimizer.settings"


def test_loading_workflow_keeps_cached_bundle_error_visible_and_blocks_auto_retry(monkeypatch, tmp_path) -> None:
    entry = SimpleNamespace(slot_name="01 - Optimizer", module_key="optimizer", readiness="ready")
    bundle = ModuleSurfaceBundle(source="cache", surfaces=(SurfaceModel("optimizer.settings", "Settings", "settings", True, "form", {}, {"parallel_workers": 2}, {"parallel_workers": 2}, ()),))
    calls: list[str] = []
    app = SimpleNamespace(
        _selected_module=entry.slot_name,
        _request_tokens={f"bundle:{entry.slot_name}": 1},
        _bundle_loading={entry.slot_name},
        _bundle_live_slots=set(),
        _bundle_failed_slots=set(),
        _bundles={entry.slot_name: bundle},
        _bundle_errors={},
        _drafts={},
        _state_root=tmp_path,
        _render=lambda: None,
        _render_detail_only=False,
    )
    monkeypatch.setattr(loading_workflow, "save_bundle_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(loading_workflow.background_jobs, "start", lambda *_args, **_kwargs: calls.append("start"))

    loading_workflow._apply_bundle(app, entry, 1, None, RuntimeError("boom"))

    assert app._bundles[entry.slot_name] is bundle
    assert app._bundle_errors[entry.slot_name] == "boom"
    assert entry.slot_name in app._bundle_failed_slots
    assert entry.slot_name not in app._bundle_live_slots
    assert loading_workflow.status_text(app, entry) == "Error (cache): boom"

    loading_workflow.ensure_bundle(app, entry)
    assert calls == []

    loading_workflow.ensure_bundle(app, entry, force=True)
    assert calls == ["start"]
    assert entry.slot_name not in app._bundle_failed_slots


def test_refresh_registry_clears_failed_bundle_slots_for_explicit_retry(monkeypatch) -> None:
    calls: list[str] = []
    app = SimpleNamespace(
        _pipeline_root="pipeline",
        _state_root="state",
        _bundle_failed_slots={"01 - Optimizer"},
        _request_tokens={},
        _render=lambda: None,
        _render_detail_only=False,
    )
    monkeypatch.setattr(loading_workflow.background_jobs, "start", lambda *_args, **_kwargs: calls.append("start"))

    loading_workflow.refresh_registry(app)

    assert app._bundle_failed_slots == set()
    assert calls == ["start"]
