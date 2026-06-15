"""UI workflow for responsive Edit Suite rendering."""

from __future__ import annotations

from ..policy import SECTION_ORDER
from . import lazy_tabs, layout, loading_workflow, rendering, responsive, view_model


def configure(app) -> None:
    if getattr(app, "_ui_workflow_ready", False):
        return
    app._ui_workflow_ready = True
    app._detail_sections = {}
    app._dirty_sections = set()
    app._section_action_widgets = {}
    responsive.activate_resize(app)
    responsive.register_resize_callback(app, "shell_layout", lambda width: layout.apply_shell_layout(app, width))
    lazy_tabs.configure(app)
    for name, _label in SECTION_ORDER:
        lazy_tabs.register_tab(app, name, lambda current_app, frame, section_name=name: _build_section(current_app, frame, section_name))


def render(app, *, detail_only: bool = False) -> None:
    entry = app._selected_entry()
    if not detail_only:
        rendering.render_shell_chrome(
            app._shell,
            source=app._snapshot.source,
            stale=app._snapshot.stale,
            message=app._snapshot.message,
            items=view_model.list_items(app._snapshot),
            selected_key=app._selected_module,
            select_module=app.select_module,
        )
    if entry is None:
        app._detail_sections = {}
        app._dirty_sections.clear()
        app._section_action_widgets.clear()
        app._action_widgets = {}
        rendering.render_detail_header(app._shell, None)
        return
    app._ensure_bundle(entry)
    detail = view_model.detail_view(
        entry,
        bundle=app._bundles.get(entry.slot_name),
        drafts=app._drafts.get(entry.slot_name),
        bundle_error=app._bundle_errors.get(entry.slot_name, ""),
        loading_message=loading_workflow.loading_message(app, entry.slot_name),
        status_text=loading_workflow.status_text(app, entry),
        operation_results=getattr(app, "_operation_results", {}),
    )
    app._detail_sections = {section.name: section for section in detail.sections}
    app._dirty_sections = set(app._detail_sections)
    app._section_action_widgets.clear()
    selected_section = view_model.preferred_section(detail.sections, app._current_section())
    app._ui_state["selected_section"] = selected_section
    rendering.render_detail_header(app._shell, detail)
    _show_section(app, selected_section)


def on_tab_selected(app) -> None:
    if getattr(app, "_suspend_tab_events", False):
        return
    section_name = lazy_tabs.selected_name(app)
    if not section_name:
        return
    app._ui_state["selected_section"] = section_name
    _render_section(app, section_name)


def _build_section(app, frame, section_name: str) -> None:
    app._shell["sections"][section_name] = layout.build_section_tab(frame)


def _show_section(app, section_name: str) -> None:
    if not section_name:
        return
    lazy_tabs.build_tab(app, section_name)
    app._suspend_tab_events = True
    try:
        app._shell["tabs"].set(section_name)
    finally:
        app._suspend_tab_events = False
    app._active_tab_name = section_name
    _render_section(app, section_name)


def _render_section(app, section_name: str) -> None:
    section = app._detail_sections.get(section_name)
    if section is None:
        app._action_widgets = {}
        return
    lazy_tabs.build_tab(app, section_name)
    if section_name in app._dirty_sections:
        container = app._shell["sections"][section_name]["scroll"]
        widgets = rendering.render_section(container, section, app=app, width=responsive.current_width(app))
        app._section_action_widgets[section_name] = widgets
        app._dirty_sections.discard(section_name)
    app._action_widgets = dict(app._section_action_widgets.get(section_name, {}))
