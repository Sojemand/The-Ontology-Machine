from __future__ import annotations


class Entry:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def delete(self, _start, _end=None) -> None:
        self._value = ""

    def insert(self, _index, value: str) -> None:
        self._value = value


class TextBox:
    def __init__(self, text: str) -> None:
        self._text = text

    def get(self, _start: str, _end: str) -> str:
        return self._text

    def delete(self, _start: str, _end: str) -> None:
        self._text = ""

    def insert(self, _start: str, text: str) -> None:
        self._text = text


class Var:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value


class BoolVar:
    def __init__(self, value: bool) -> None:
        self._value = value

    def get(self) -> bool:
        return self._value


def picker(selected: set[str], options: list[str]) -> dict:
    return {"vars": {value: BoolVar(value in selected) for value in options}}
