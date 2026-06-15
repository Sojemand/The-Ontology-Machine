from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

JsonObject = dict[str, Any]

SEMANTIC_RELEASE_ACTIVE = "semantic_release_active"
FILLED_DATABASE = "filled"
EMPTY_DATABASE = "empty"


def _copy_mapping(value: Mapping[str, Any] | None = None) -> JsonObject:
    return deepcopy(dict(value or {}))


def _copy_sequence(value: Sequence[Any] | None = None) -> list[Any]:
    return deepcopy(list(value or ()))
