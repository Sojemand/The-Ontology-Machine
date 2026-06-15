from __future__ import annotations

from orchestrator.ui import responsive, theme


def test_theme_contract_matches_pipeline_standard() -> None:
    assert theme.APPEARANCE_MODE == "dark"
    assert theme.COLOR_THEME == "blue"
    assert theme.FONT_FAMILY == "Segoe UI"
    assert theme.FONT_SIZE_NORMAL == 13
    assert theme.FONT_SIZE_SMALL == 11
    assert theme.FONT_SIZE_HEADER == 16
    assert theme.FONT_SIZE_MONO == 11
    assert theme.WINDOW_MIN_WIDTH == 960
    assert theme.WINDOW_MIN_HEIGHT == 720
    assert theme.INPUT_HEIGHT == 34
    assert theme.BUTTON_HEIGHT == 38
    assert theme.ACTION_BUTTON_HEIGHT == 42
    assert theme.PADDING == 12
    assert theme.PADDING_SMALL == 6
    assert theme.PADDING_LARGE == 20
    assert theme.COLOR_ACCENT == "#3B8ED0"
    assert theme.COLOR_WARNING == "#FFA500"
    assert theme.COLOR_SUCCESS == "#00CC66"
    assert theme.COLOR_ERROR == "#FF4444"
    assert theme.STATUS_READY == "Ready"
    assert theme.STATUS_DONE == "Done"
    assert theme.STATUS_ERROR == "Error"
    assert theme.font_normal() == ("Segoe UI", 13)
    assert theme.font_small() == ("Segoe UI", 11)
    assert theme.font_header() == ("Segoe UI", 16, "bold")
    assert theme.font_mono() == ("Consolas", 11)


def test_fit_window_geometry_targets_small_laptop_safely() -> None:
    class _Screen:
        def winfo_screenwidth(self):
            return 1366

        def winfo_screenheight(self):
            return 768

    assert responsive.fit_window_geometry(_Screen()) == "1280x720+43+16"
