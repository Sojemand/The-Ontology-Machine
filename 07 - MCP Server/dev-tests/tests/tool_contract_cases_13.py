from __future__ import annotations

from tests.tool_contract_matrix_types import GoldenCase

RUNTIME_POLICY = {
    "LOG_LEVEL": "INFO",
    "DEBUG_BUNDLE_DIR": "",
    "PAGE_ASSET_ALLOWED_ROOTS": "",
    "OPENAI_API_BASE_URL": "https://api.openai.com/v1",
}


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "interpreter.describe_surfaces",
            lambda _p: {},
            edit_calls=lambda _p: [("interpreter", {"action": "describe_surfaces"})],
        ),
        GoldenCase(
            "interpreter.read_surface",
            lambda _p: {"surface_id": "interpreter.runtime_policy_env"},
            edit_calls=lambda _p: [
                ("interpreter", {"action": "read_surface", "surface_id": "interpreter.runtime_policy_env"})
            ],
        ),
        GoldenCase(
            "interpreter.validate_surface",
            lambda _p: {"surface_id": "interpreter.runtime_policy_env", "value": RUNTIME_POLICY},
            edit_calls=lambda _p: [
                (
                    "interpreter",
                    {"action": "validate_surface", "surface_id": "interpreter.runtime_policy_env", "value": RUNTIME_POLICY},
                )
            ],
        ),
        GoldenCase(
            "interpreter.write_surface",
            lambda _p: {"surface_id": "interpreter.runtime_policy_env", "value": RUNTIME_POLICY},
            edit_calls=lambda _p: [
                (
                    "interpreter",
                    {"action": "write_surface", "surface_id": "interpreter.runtime_policy_env", "value": RUNTIME_POLICY},
                )
            ],
        ),
    ]
