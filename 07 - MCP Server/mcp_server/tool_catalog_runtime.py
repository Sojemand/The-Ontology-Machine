from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _artifact_properties, _enum, _tool


def runtime_tools() -> list[dict[str, Any]]:
    return [
        _tool("inspect_runtime", "Inspect orchestrator-owned runtime settings and credential readiness.", {}),
        _tool(
            "read_runtime_settings",
            "Read orchestrator-owned runtime settings.",
            {},
        ),
        _tool(
            "write_runtime_settings",
            "Write orchestrator-owned runtime settings.",
            {
                "settings": {"type": "object", "additionalProperties": True},
            },
            required=("settings",),
        ),
        _tool(
            "reset_runtime_settings",
            "Reset orchestrator-owned runtime settings to owner defaults.",
            {},
        ),
        _tool(
            "inspect_runtime_credentials",
            "Inspect orchestrator-owned API-key credential readiness without revealing secret values.",
            {},
        ),
        _tool(
            "set_runtime_api_key",
            "Set one orchestrator-owned API-key credential.",
            {
                "target": {"type": "string", "enum": ["llm_shared", "embeddings"]},
                "secret_value": {"type": "string"},
            },
            required=("target", "secret_value"),
        ),
        _tool(
            "delete_runtime_api_key",
            "Delete one orchestrator-owned API-key credential.",
            {
                "target": {"type": "string", "enum": ["llm_shared", "embeddings"]},
            },
            required=("target",),
        ),
        _tool(
            "reveal_secret",
            "Reveal an orchestrator-owned API key with explicit unlock phrase and audit.",
            {
                "target": {"type": "string", "enum": ["llm_shared", "embeddings"]},
                "purpose": {"type": "string"},
                "unlock_phrase": {"type": "string"},
            },
            required=("target", "purpose", "unlock_phrase"),
        ),
    ]
