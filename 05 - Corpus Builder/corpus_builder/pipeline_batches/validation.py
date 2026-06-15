from __future__ import annotations

from typing import Any


def passthrough_command(payload: dict[str, Any]) -> dict[str, Any]:
    return payload
