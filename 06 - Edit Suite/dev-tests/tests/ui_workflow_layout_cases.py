from __future__ import annotations

from edit_suite.ui import layout, surface_cards
from ui_workflow_support import GridApp, GridWidget


def test_layout_mode_and_form_mode_switch_at_compact_threshold() -> None:
    assert layout.layout_mode_for_width(1179) == "compact"
    assert layout.layout_mode_for_width(1180) == "wide"
    assert surface_cards.uses_compact_form_layout(1179) is True
    assert surface_cards.uses_compact_form_layout(1180) is False


def test_apply_shell_layout_stacks_sidebar_above_detail_in_compact_mode(monkeypatch) -> None:
    monkeypatch.setattr(layout.responsive, "remember_layout_key", lambda *_args, **_kwargs: True)
    app = GridApp()
    shell = {key: GridWidget() for key in ("sidebar", "detail", "module_scroll", "subtitle_label", "status_label")}
    app._shell = shell

    layout.apply_shell_layout(app, 960)

    assert shell["sidebar"].grid_calls[-1]["row"] == 0
    assert shell["detail"].grid_calls[-1]["row"] == 1
    assert shell["detail"].grid_calls[-1]["column"] == 0
    assert shell["module_scroll"].configure_calls[-1] == {"height": layout.COMPACT_MODULE_SCROLL_HEIGHT}
