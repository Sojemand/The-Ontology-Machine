from __future__ import annotations

from typing import Any, Mapping


def build_collision_summary(collisions: list[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "total": len(collisions),
        "requires_user_choice": sum(
            1
            for item in collisions
            if item.get("requires_user_choice") or item.get("resolution_status") == "requires_user_choice"
        ),
        "unresolved": sum(1 for item in collisions if item.get("resolution_status") in {"unresolved", "requires_user_choice"}),
        "resolved": sum(1 for item in collisions if item.get("resolution_status") == "resolved"),
    }
