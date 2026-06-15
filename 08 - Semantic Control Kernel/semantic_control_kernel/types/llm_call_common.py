from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence


JsonObject = dict[str, Any]


def _copy_mapping(value: Mapping[str, Any] | None) -> JsonObject:
    return deepcopy(dict(value or {}))


def _copy_sequence(value: Sequence[Any] | None) -> list[Any]:
    return deepcopy(list(value or ()))
