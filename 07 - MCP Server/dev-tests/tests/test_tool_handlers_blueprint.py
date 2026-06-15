from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mcp_server import support_monitor, tool_handlers
from mcp_server.contract_client import ContractError
from mcp_server.tools import ToolFailure, call_tool

def test_create_new_corpus_from_blueprint_is_retired() -> None:
    with pytest.raises(ToolFailure, match="Unbekanntes Tool"):
        call_tool("create_new_corpus_from_blueprint", {})


def test_release_exports_reject_mcp_semantic_release_state(tmp_path: Path) -> None:
    blocked = tool_handlers._state_dir() / "semantic_releases" / "default.semantic_release.json"

    with pytest.raises(ToolFailure, match="state/semantic_releases"):
        call_tool("export_default_blueprint_release", {"output_path": str(blocked)})
