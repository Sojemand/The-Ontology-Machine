from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def tuple_of_str(value: tuple[str, ...] | list[str] | set[str] | None) -> tuple[str, ...]:
    return tuple(str(item) for item in (value or ()))
