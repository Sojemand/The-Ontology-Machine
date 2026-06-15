from __future__ import annotations


class PopupStub:
    def __init__(self, *_args, **_kwargs) -> None:
        self.bindings: dict[str, object] = {}
        self.destroyed = False

    def overrideredirect(self, _value) -> None:
        return None

    def attributes(self, *_args) -> None:
        return None

    def geometry(self, _value: str) -> None:
        return None

    def bind(self, sequence: str, callback) -> None:
        self.bindings[sequence] = callback

    def lift(self) -> None:
        return None

    def winfo_exists(self) -> bool:
        return not self.destroyed

    def destroy(self) -> None:
        self.destroyed = True


class FocusWidget:
    def __init__(self) -> None:
        self.focus_calls = 0
        self.bindings: dict[str, object] = {}

    def focus_force(self) -> None:
        self.focus_calls += 1

    def bind(self, sequence: str, callback) -> None:
        self.bindings[sequence] = callback


class TkListboxStub(FocusWidget):
    def __init__(self, *_args, **_kwargs) -> None:
        super().__init__()
        self.items: list[str] = []
        self.scroll_calls: list[tuple[int, str]] = []
        self.selection: tuple[int, ...] = ()

    def pack(self, *_args, **_kwargs) -> None:
        return None

    def insert(self, _index, value: str) -> None:
        self.items.append(value)

    def configure(self, **_kwargs) -> None:
        return None

    def curselection(self):
        return self.selection

    def get(self, index: int) -> str:
        return self.items[index]

    def yview(self, *_args, **_kwargs) -> None:
        return None

    def yview_scroll(self, steps: int, units: str) -> None:
        self.scroll_calls.append((steps, units))


class TkScrollbarStub(FocusWidget):
    def __init__(self, *_args, **_kwargs) -> None:
        super().__init__()
        self.command = None

    def pack(self, *_args, **_kwargs) -> None:
        return None

    def configure(self, **kwargs) -> None:
        if "command" in kwargs:
            self.command = kwargs["command"]

    def set(self, *_args, **_kwargs) -> None:
        return None


class MeasuredTextboxStub:
    def __init__(self, *_args, **kwargs) -> None:
        self._config = dict(kwargs)
        self._text = ""
        self._display_lines = 3
        self._bindings: dict[str, object] = {}

    def pack(self, *_args, **_kwargs):
        return None

    def grid(self, *_args, **_kwargs):
        return None

    def bind(self, sequence: str, callback) -> None:
        self._bindings[sequence] = callback

    def configure(self, **kwargs) -> None:
        self._config.update(kwargs)

    def cget(self, key: str):
        return self._config.get(key)

    def delete(self, *_args) -> None:
        self._text = ""

    def insert(self, _index, text: str) -> None:
        self._text = text

    def update_idletasks(self) -> None:
        return None

    def after_idle(self, callback) -> None:
        callback()

    def dlineinfo(self, index: str):
        if not self._text:
            return None
        if index == "1.0":
            return (0, 3, 0, 18, 0)
        if index == "end-1c":
            return None
        return None

    def count(self, _start: str, _end: str, _mode: str):
        return (self._display_lines,)


class AfterTextboxStub(MeasuredTextboxStub):
    def __init__(self, *_args, **kwargs) -> None:
        super().__init__(*_args, **kwargs)
        self.configure_calls: list[dict[str, object]] = []

    def configure(self, **kwargs) -> None:
        self.configure_calls.append(dict(kwargs))
        super().configure(**kwargs)
