from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.repository.paths import StatePaths


MODULE_ROOT = Path(__file__).resolve().parents[2]


def isolated_state_paths(tmp_path: Path) -> StatePaths:
    return StatePaths(module_root=MODULE_ROOT, state_root=(tmp_path / "state").resolve())


def mcp_request(tool_name: str) -> dict[str, object]:
    return {
        "schema_version": "semantic_control_kernel.mcp_request.v1",
        "transport": "stdio",
        "tool_name": tool_name,
        "visibility": "agent_visible",
        "model_arguments": {},
        "client_context": {
            "host_surface_identity": "test_host",
            "client_request_id": "req_phase7",
        },
        "event_scope": None,
    }
