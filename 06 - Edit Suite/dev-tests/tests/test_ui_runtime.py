from __future__ import annotations

from types import SimpleNamespace

from edit_suite.ui import lazy_tabs, responsive
from edit_suite.ui.scoped_scroll import _nearest_scroll_canvas, _widget_has_native_scroll


class _ResizeApp:
    def __init__(self, width: int = 960) -> None:
        self.width = width
        self.bindings = {}
        self.after_idle_jobs = []

    def winfo_width(self) -> int:
        return self.width

    def bind(self, sequence: str, callback) -> None:
        self.bindings[sequence] = callback

    def after_idle(self, callback) -> None:
        self.after_idle_jobs.append(callback)


class _Screen:
    def winfo_screenwidth(self) -> int:
        return 1366

    def winfo_screenheight(self) -> int:
        return 768


class _FakeTabs:
    def __init__(self) -> None:
        self.frames = {}
        self.selected = ""

    def add(self, name: str):
        frame = SimpleNamespace(name=name)
        self.frames[name] = frame
        if not self.selected:
            self.selected = name
        return frame

    def set(self, name: str) -> None:
        self.selected = name

    def get(self) -> str:
        return self.selected


def test_fit_window_geometry_targets_small_laptop_safely() -> None:
    assert responsive.fit_window_geometry(_Screen()) == "1280x720+43+16"


def test_restore_window_geometry_recenters_invalid_saved_position() -> None:
    restored = responsive.restore_window_geometry(_Screen(), "1400x900+50+50")

    assert restored == "1294x720+36+16"


def test_activate_resize_deduplicates_pending_dispatches() -> None:
    app = _ResizeApp()
    calls: list[int] = []

    responsive.register_resize_callback(app, "shell", lambda width: calls.append(width))
    app.bindings["<Configure>"]()
    app.bindings["<Configure>"]()

    assert len(app.after_idle_jobs) == 1
    assert calls == [960]

    app.after_idle_jobs.pop()()

    assert calls == [960, 960]


def test_lazy_tabs_build_once_and_track_selected_name() -> None:
    app = SimpleNamespace(_shell={"tabs": _FakeTabs()})
    builds: list[str] = []

    lazy_tabs.register_tab(app, "Summary", lambda _app, frame: builds.append(frame.name))

    lazy_tabs.build_tab(app, "Summary")
    lazy_tabs.build_tab(app, "Summary")
    lazy_tabs.activate(app, "Summary")

    assert builds == ["Summary"]
    assert lazy_tabs.is_built(app, "Summary") is True
    assert lazy_tabs.selected_name(app) == "Summary"


def test_scoped_scroll_picks_nearest_registered_canvas() -> None:
    outer = type("Canvas", (), {"_edit_suite_scroll_canvas": True, "master": None})()
    inner = type("Canvas", (), {"_edit_suite_scroll_canvas": True, "master": outer})()
    child = type("Label", (), {"master": inner})()

    assert _nearest_scroll_canvas(child) is inner


def test_scoped_scroll_defers_to_native_text_widgets() -> None:
    canvas = type("Canvas", (), {"_edit_suite_scroll_canvas": True, "master": None})()
    text_widget = type("Text", (), {"master": canvas})()

    assert _widget_has_native_scroll(text_widget, stop=canvas) is True
