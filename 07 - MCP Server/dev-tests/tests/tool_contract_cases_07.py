from __future__ import annotations

from tests.tool_contract_matrix_helpers import _artifact_args, _reset_workspace_paths, _support_incident, _working_workspace_paths, _workspace_paths
from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "inspect_runtime_credentials",
            lambda _p: {},
            admin_calls=lambda _p: [
                ("orchestrator", {"action": "manage_credentials", "operation": "inspect"})
            ],
        ),
        GoldenCase(
            "set_runtime_api_key",
            lambda _p: {"target": "llm_shared", "secret_value": "test-secret"},
            admin_calls=lambda _p: [
                (
                    "orchestrator",
                    {
                        "action": "manage_credentials",
                        "operation": "set_api_key",
                        "target": "llm_shared",
                        "secret_value": "test-secret",
                    },
                )
            ],
        ),
        GoldenCase(
            "delete_runtime_api_key",
            lambda _p: {"target": "llm_shared"},
            admin_calls=lambda _p: [
                (
                    "orchestrator",
                    {
                        "action": "manage_credentials",
                        "operation": "delete_api_key",
                        "target": "llm_shared",
                    },
                )
            ],
        ),
        GoldenCase(
            "reveal_secret",
            lambda _p: {"target": "llm_shared", "purpose": "contract test", "unlock_phrase": "REVEAL_SECRET:llm_shared"},
            admin_calls=lambda _p: [
                (
                    "orchestrator",
                    {
                        "action": "reveal_secret",
                        "target": "llm_shared",
                        "purpose": "contract test",
                        "unlock_phrase": "REVEAL_SECRET:llm_shared",
                    },
                )
            ],
        ),
    ]
