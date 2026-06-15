from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest

from mcp_server import support_monitor, tool_handlers
from mcp_server.tools import ToolFailure, call_tool, tool_definitions


Call = tuple[str, dict[str, Any]]
ArgsFactory = Callable[[dict[str, str]], dict[str, Any]]
CallsFactory = Callable[[dict[str, str]], list[Call]]


@dataclass(frozen=True)
class GoldenCase:
    name: str
    arguments: ArgsFactory
    product_calls: CallsFactory = lambda _paths: []
    edit_calls: CallsFactory = lambda _paths: []
    admin_calls: CallsFactory = lambda _paths: []
