from __future__ import annotations

import sys

from mcp_server.protocol import handle_message
from mcp_server.semantic_control_kernel_visibility import LEGACY_RETIRED_TOOL_NAMES


def test_old_public_kernel_names_fail_closed_before_legacy_handler_import() -> None:
    sys.modules.pop("mcp_server.tool_handlers_semantic_kernel", None)

    for tool_name in LEGACY_RETIRED_TOOL_NAMES:
        response = handle_message(
            {
                "jsonrpc": "2.0",
                "id": tool_name,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": {}},
            }
        )
        assert response is not None
        payload = response["result"]["structuredContent"]
        assert payload["status"] == "rejected"
        assert payload["tool_name"] == tool_name
        assert payload["error"]["code"] == "legacy_kernel_surface_retired"

    assert "mcp_server.tool_handlers_semantic_kernel" not in sys.modules
