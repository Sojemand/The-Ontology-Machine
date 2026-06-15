"""Small widget helpers for the Orchestrator model settings UI."""

from __future__ import annotations

from . import theme


def font_size(font) -> int:
    if isinstance(font, tuple) and len(font) >= 2:
        try:
            return max(int(font[1]), 11)
        except (TypeError, ValueError):
            return theme.FONT_SIZE_SMALL
    return theme.FONT_SIZE_SMALL


def widget_exists(widget) -> bool:
    if widget is None:
        return False
    probe = getattr(widget, "winfo_exists", None)
    if probe is None:
        return True
    try:
        return bool(probe())
    except Exception:
        return False


def focus_widget(widget) -> None:
    if widget is None:
        return
    focus_force = getattr(widget, "focus_force", None)
    if callable(focus_force):
        try:
            focus_force()
            return
        except Exception:
            pass
    focus_set = getattr(widget, "focus_set", None)
    if callable(focus_set):
        try:
            focus_set()
        except Exception:
            pass


def bind_popup_focus(widget, focus_target) -> None:
    bind = getattr(widget, "bind", None)
    if callable(bind):
        bind("<Enter>", lambda _event: focus_widget(focus_target))


def bind_listbox_wheel(widget, listbox) -> None:
    bind = getattr(widget, "bind", None)
    if not callable(bind):
        return
    bind("<MouseWheel>", lambda event: scroll_listbox_wheel(listbox, event))
    bind("<Button-4>", lambda event: scroll_listbox_wheel(listbox, event))
    bind("<Button-5>", lambda event: scroll_listbox_wheel(listbox, event))


def scroll_listbox_wheel(listbox, event) -> str:
    delta = coerce_event_int(getattr(event, "delta", 0))
    button = coerce_event_int(getattr(event, "num", 0))
    if button == 4:
        steps = -1
    elif button == 5:
        steps = 1
    elif delta:
        magnitude = max(abs(delta) // 120, 1)
        steps = -magnitude if delta > 0 else magnitude
    else:
        return "break"
    yview_scroll = getattr(listbox, "yview_scroll", None)
    if callable(yview_scroll):
        yview_scroll(steps, "units")
    return "break"


def coerce_event_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def coerce_widget_height(widget) -> int:
    try:
        return int(getattr(widget, "cget", lambda _key: 0)("height") or 0)
    except (TypeError, ValueError):
        return 0


def coerce_widget_width(widget) -> int:
    try:
        return int(getattr(widget, "cget", lambda _key: 0)("width") or 0)
    except (TypeError, ValueError):
        return 0


def line_info(widget, index: str):
    dlineinfo = getattr(widget, "dlineinfo", None)
    if not callable(dlineinfo):
        return None
    try:
        info = dlineinfo(index)
    except Exception:
        return None
    if not info or len(info) < 4:
        return None
    try:
        return tuple(int(value) for value in info[:5])
    except (TypeError, ValueError):
        return None


def display_line_count(widget, *, has_text: bool) -> int:
    if not has_text:
        return 1
    text_widget = getattr(widget, "_textbox", widget)
    count = getattr(text_widget, "count", None)
    if callable(count):
        try:
            result = count("1.0", "end-1c", "displaylines")
        except Exception:
            result = None
        raw = result[0] if isinstance(result, tuple) and result else result
        lines = coerce_event_int(raw)
        if lines > 0:
            return lines
    first_line = line_info(widget, "1.0")
    last_line = line_info(widget, "end-1c")
    if first_line is None or last_line is None:
        return 0
    line_height = max(int(first_line[3]), 1)
    offset = max(int(last_line[1]) - int(first_line[1]), 0)
    return max((offset // line_height) + 1, 1)
