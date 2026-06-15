from __future__ import annotations

from types import SimpleNamespace

from orchestrator.ui import rendering


class _TextBox:
    def __init__(self) -> None:
        self.value = ""
        self.states: list[str] = []
        self.see_calls = 0

    def configure(self, **kwargs) -> None:
        state = kwargs.get("state")
        if state is not None:
            self.states.append(str(state))

    def insert(self, _index: str, value: str) -> None:
        self.value += value

    def delete(self, _start: str, _end: str) -> None:
        self.value = ""

    def see(self, _index: str) -> None:
        self.see_calls += 1


def test_append_log_buffers_lines_until_log_tab_exists() -> None:
    app = SimpleNamespace()

    rendering.append_log(app, "first")
    rendering.append_log(app, "second")

    assert app._log_lines == ["first\n", "second\n"]
    assert not hasattr(app, "_log_box")

    app._log_box = _TextBox()
    rendering.sync_log_box(app)

    assert app._log_box.value == "first\nsecond\n"
    assert app._log_box.states == ["normal", "disabled"]
    assert app._log_box.see_calls == 1


def test_clear_log_resets_buffer_before_log_tab_exists() -> None:
    app = SimpleNamespace()

    rendering.append_log(app, "first")
    rendering.clear_log(app)
    app._log_box = _TextBox()
    rendering.sync_log_box(app)

    assert app._log_lines == []
    assert app._log_box.value == ""
