from __future__ import annotations

from typing import Any, Callable


class ToolFailure(RuntimeError):
    """Raised for user-visible MCP tool errors."""


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]

__all__ = [name for name in globals() if not name.startswith("__")]
