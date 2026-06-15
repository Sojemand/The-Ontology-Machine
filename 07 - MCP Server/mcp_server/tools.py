"""Path-stable facade for MCP tool catalog and handlers."""

from __future__ import annotations

from .permissions import visible_tool_definitions
from .tool_catalog import tool_definitions
from .tool_handlers import ToolFailure, call_tool, result_as_text

__all__ = ["ToolFailure", "call_tool", "result_as_text", "tool_definitions", "visible_tool_definitions"]
