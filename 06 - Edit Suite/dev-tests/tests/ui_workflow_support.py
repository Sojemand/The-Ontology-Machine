from __future__ import annotations

from types import SimpleNamespace


class GridWidget:
    def __init__(self) -> None:
        self.grid_calls = []
        self.configure_calls = []
        self.column_calls = []
        self.row_calls = []

    def grid(self, **kwargs) -> None:
        self.grid_calls.append(kwargs)

    def configure(self, **kwargs) -> None:
        self.configure_calls.append(kwargs)

    def grid_columnconfigure(self, column: int, weight: int) -> None:
        self.column_calls.append((column, weight))

    def grid_rowconfigure(self, row: int, weight: int) -> None:
        self.row_calls.append((row, weight))


class GridApp(GridWidget):
    pass


class FakeTabs:
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
