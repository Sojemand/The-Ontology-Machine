from __future__ import annotations

from types import SimpleNamespace

from edit_suite.surfaces.types import SectionModel, SurfaceModel
from edit_suite.ui import lazy_tabs, workflow
from edit_suite.ui.view_model import DetailView
from ui_workflow_support import FakeTabs


def test_workflow_renders_only_active_section_and_skips_sidebar_on_detail_refresh(monkeypatch) -> None:
    surface = SurfaceModel("optimizer.settings", "Settings", "settings", True, "form", {}, {"parallel_workers": 1}, {"parallel_workers": 1}, ())
    detail = DetailView(
        title="Optimizer",
        subtitle="optimizer",
        status="ready",
        sections=(
            SectionModel("Summary", "Summary", "summary", "body"),
            SectionModel("Settings", "Settings", "settings", "body", surfaces=(surface,)),
            SectionModel("Preview/Drift", "Preview/Drift", "preview", "body"),
        ),
    )
    entry = SimpleNamespace(slot_name="01 - Optimizer")
    chrome_calls: list[str] = []
    section_calls: list[str] = []
    app = SimpleNamespace(
        _shell={"tabs": FakeTabs(), "sections": {}, "module_buttons": {}},
        _snapshot=SimpleNamespace(source="live", stale=False, message="", entries=(entry,)),
        _selected_module=entry.slot_name,
        _bundles={},
        _bundle_errors={},
        _drafts={},
        _ui_state={"selected_section": "Summary"},
        _action_widgets={},
        select_module=lambda *_args: None,
    )
    app._selected_entry = lambda: entry
    app._current_section = lambda: app._shell["tabs"].get()
    app._ensure_bundle = lambda _entry: None

    monkeypatch.setattr(workflow.responsive, "activate_resize", lambda _app: None)
    monkeypatch.setattr(workflow.responsive, "register_resize_callback", lambda _app, _key, _callback: None)
    monkeypatch.setattr(workflow.view_model, "list_items", lambda _snapshot: ())
    monkeypatch.setattr(workflow.view_model, "detail_view", lambda *_args, **_kwargs: detail)
    monkeypatch.setattr(workflow.layout, "build_section_tab", lambda frame: {"tab": frame, "scroll": frame})
    monkeypatch.setattr(workflow.rendering, "render_shell_chrome", lambda *_args, **_kwargs: chrome_calls.append("chrome"))
    monkeypatch.setattr(workflow.rendering, "render_detail_header", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        workflow.rendering,
        "render_section",
        lambda _container, section, *, app, width: section_calls.append(section.name) or {section.name: {"surface": None, "editor": None}},
    )

    workflow.configure(app)
    workflow.render(app)

    assert chrome_calls == ["chrome"]
    assert section_calls == ["Settings"]
    assert lazy_tabs.is_built(app, "Settings") is True
    assert lazy_tabs.is_built(app, "Summary") is False
    assert app._action_widgets == {"Settings": {"surface": None, "editor": None}}

    app._shell["tabs"].set("Summary")
    workflow.on_tab_selected(app)

    assert section_calls == ["Settings", "Summary"]

    app._shell["tabs"].set("Settings")
    workflow.render(app, detail_only=True)

    assert chrome_calls == ["chrome"]
    assert section_calls[-1] == "Settings"


def test_workflow_passes_loading_state_into_detail_view(monkeypatch) -> None:
    captured = {}
    entry = SimpleNamespace(slot_name="01 - Optimizer", readiness="ready")
    app = SimpleNamespace(
        _shell={"tabs": FakeTabs(), "sections": {}, "module_buttons": {}},
        _snapshot=SimpleNamespace(source="cache", stale=False, message="", entries=(entry,)),
        _selected_module=entry.slot_name,
        _bundles={},
        _bundle_errors={},
        _bundle_loading=set(),
        _drafts={},
        _ui_state={"selected_section": "Summary"},
        _action_widgets={},
        select_module=lambda *_args: None,
    )
    app._selected_entry = lambda: entry
    app._current_section = lambda: app._shell["tabs"].get()
    app._ensure_bundle = lambda _entry: app._bundle_loading.add(entry.slot_name)
    monkeypatch.setattr(workflow.responsive, "activate_resize", lambda _app: None)
    monkeypatch.setattr(workflow.responsive, "register_resize_callback", lambda _app, _key, _callback: None)
    monkeypatch.setattr(workflow.view_model, "list_items", lambda _snapshot: ())
    monkeypatch.setattr(workflow.view_model, "detail_view", lambda *_args, **kwargs: captured.update(kwargs) or DetailView("Module", "module", kwargs["status_text"], (SectionModel("Summary", "Summary", "summary", "body"),)))
    monkeypatch.setattr(workflow.layout, "build_section_tab", lambda frame: {"tab": frame, "scroll": frame})
    monkeypatch.setattr(workflow.rendering, "render_shell_chrome", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(workflow.rendering, "render_detail_header", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(workflow.rendering, "render_section", lambda *_args, **_kwargs: {})

    workflow.configure(app)
    workflow.render(app)

    assert captured["loading_message"] == "Loading..."
    assert captured["status_text"] == "Loading..."
