from __future__ import annotations


class Widget:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.config: dict[str, object] = {}
        self.visible = True

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value

    def pack(self, **_kwargs) -> None:
        self.visible = True

    def pack_forget(self) -> None:
        self.visible = False

    def grid(self, **_kwargs) -> None:
        self.visible = True

    def grid_forget(self) -> None:
        self.visible = False

    def delete(self, *_args) -> None:
        self.value = ""

    def insert(self, *_args) -> None:
        self.value = str(_args[-1])

    def configure(self, **kwargs) -> None:
        self.config.update(kwargs)
        if "text" in kwargs:
            self.value = str(kwargs["text"])

    def destroy(self) -> None:
        return None

    def winfo_children(self) -> list[object]:
        return []


class TextBox(Widget):
    pass


class RowWidget:
    def __init__(self) -> None:
        self.visible = True

    def pack(self, **_kwargs) -> None:
        self.visible = True

    def pack_forget(self) -> None:
        self.visible = False

    def grid(self, **_kwargs) -> None:
        self.visible = True

    def grid_forget(self) -> None:
        self.visible = False
