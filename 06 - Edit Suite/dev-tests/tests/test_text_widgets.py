from __future__ import annotations

from edit_suite.ui import text_widgets


class _FakeInnerTextbox:
    def __init__(self, selection_text: str | None = None) -> None:
        self.selection_text = selection_text
        self.configure_calls: list[dict[str, object]] = []
        self.bindings: dict[str, dict[str, object]] = {}

    def configure(self, **kwargs) -> None:
        self.configure_calls.append(kwargs)

    def bind(self, sequence: str, command, add=None) -> None:
        self.bindings[sequence] = {"command": command, "add": add}

    def get(self, start: str, end: str) -> str:
        if self.selection_text is None:
            raise RuntimeError("no selection")
        assert (start, end) == ("sel.first", "sel.last")
        return self.selection_text


class _FakeWidget:
    def __init__(self, selection_text: str | None = None) -> None:
        self._textbox = _FakeInnerTextbox(selection_text)
        self.clipboard_events: list[tuple[str, str | None]] = []

    def clipboard_clear(self) -> None:
        self.clipboard_events.append(("clear", None))

    def clipboard_append(self, value: str) -> None:
        self.clipboard_events.append(("append", value))


def test_bind_copy_support_registers_both_shortcuts_and_callback_accepts_optional_event() -> None:
    widget = _FakeWidget("selected text")

    text_widgets._bind_copy_support(widget)

    assert widget._textbox.configure_calls == [{"cursor": "xterm", "insertwidth": 0, "takefocus": True}]
    assert set(widget._textbox.bindings) == {"<Control-c>", "<Control-C>"}
    assert widget._textbox.bindings["<Control-c>"]["add"] == "+"
    assert widget._textbox.bindings["<Control-C>"]["add"] == "+"

    lower_handler = widget._textbox.bindings["<Control-c>"]["command"]
    upper_handler = widget._textbox.bindings["<Control-C>"]["command"]

    assert lower_handler is upper_handler
    assert lower_handler(object()) == "break"
    assert upper_handler() == "break"
    assert widget.clipboard_events == [
        ("clear", None),
        ("append", "selected text"),
        ("clear", None),
        ("append", "selected text"),
    ]


def test_copy_selection_copies_selected_text_and_stops_default_handling() -> None:
    widget = _FakeWidget("copied value")

    result = text_widgets._copy_selection(widget)

    assert result == "break"
    assert widget.clipboard_events == [("clear", None), ("append", "copied value")]


def test_copy_selection_returns_break_when_no_selection_exists() -> None:
    widget = _FakeWidget()

    result = text_widgets._copy_selection(widget)

    assert result == "break"
    assert widget.clipboard_events == []
