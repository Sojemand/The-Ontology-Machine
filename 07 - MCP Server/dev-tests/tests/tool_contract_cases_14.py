from __future__ import annotations

from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "validator.describe_surfaces",
            lambda _p: {},
            edit_calls=lambda _p: [("validator", {"action": "describe_surfaces"})],
        ),
        GoldenCase(
            "validator.read_surface",
            lambda _p: {"surface_id": "validator.settings"},
            edit_calls=lambda _p: [("validator", {"action": "read_surface", "surface_id": "validator.settings"})],
        ),
        GoldenCase(
            "validator.validate_surface",
            lambda _p: {
                "surface_id": "validator.report_preview_policy",
                "value": {"flag_needs_review": True, "max_issues_per_check": 20},
            },
            edit_calls=lambda _p: [
                (
                    "validator",
                    {
                        "action": "validate_surface",
                        "surface_id": "validator.report_preview_policy",
                        "value": {"flag_needs_review": True, "max_issues_per_check": 20},
                    },
                )
            ],
        ),
        GoldenCase(
            "validator.write_surface",
            lambda _p: {
                "surface_id": "validator.report_preview_policy",
                "value": {"flag_needs_review": False, "max_issues_per_check": 7},
            },
            edit_calls=lambda _p: [
                (
                    "validator",
                    {
                        "action": "write_surface",
                        "surface_id": "validator.report_preview_policy",
                        "value": {"flag_needs_review": False, "max_issues_per_check": 7},
                    },
                )
            ],
        ),
    ]
