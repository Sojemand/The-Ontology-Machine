from __future__ import annotations

from pathlib import Path

from tests.tool_contract_matrix_recorder import _active_release_payload
from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "interpreter.interpret_document",
            lambda p: {
                "request_root": str(Path(p["interpreter_request"]).parent),
                "request_path": p["interpreter_request"],
                "output_root": p["structured_dir"],
                "structured_output_path": str(Path(p["structured_dir"]) / "Fantasy_Story.structured.json"),
                "runtime_settings": {"model": "gpt-test", "max_output_tokens": 8000},
            },
            product_calls=lambda p: [
                (
                    "interpreter",
                    {
                        "action": "interpret_document",
                        "request_path": _resolved(p["interpreter_request"]),
                        "structured_output_path": _resolved(str(Path(p["structured_dir"]) / "Fantasy_Story.structured.json")),
                        "runtime_settings": {"model": "gpt-test", "max_output_tokens": 8000},
                    },
                )
            ],
        ),
        GoldenCase(
            "interpreter.healthcheck",
            lambda _p: {"runtime_settings": {"model": "gpt-test", "max_output_tokens": 1024}},
            product_calls=lambda _p: [
                (
                    "interpreter",
                    {
                        "action": "healthcheck",
                        "runtime_settings": {"model": "gpt-test", "max_output_tokens": 1024},
                    },
                )
            ],
        ),
        GoldenCase(
            "validator.validate_document",
            lambda p: {
                "structured_root": p["structured_dir"],
                "structured_path": p["structured_artifact"],
                "validation_root": p["validation_dir"],
                "validation_output_path": str(Path(p["validation_dir"]) / "invoice.vision_validation_report.json"),
                "raw_root": p["raw_dir"],
                "raw_path": p["raw_artifact"],
            },
            product_calls=lambda p: [
                (
                    "validator",
                    {
                        "action": "validate_document",
                        "structured_path": _resolved(p["structured_artifact"]),
                        "validation_output_path": _resolved(str(Path(p["validation_dir"]) / "invoice.vision_validation_report.json")),
                        "raw_path": _resolved(p["raw_artifact"]),
                    },
                )
            ],
        ),
        GoldenCase(
            "validator.healthcheck",
            lambda _p: {},
            product_calls=lambda _p: [("validator", {"action": "healthcheck"})],
        ),
        GoldenCase(
            "normalizer.normalize_document",
            lambda p: {
                "structured_root": str(Path(p["normalizer_structured"]).parent),
                "structured_path": p["normalizer_structured"],
                "normalized_root": str(Path(p["expected_normalized"]).parent),
                "normalized_output_path": p["expected_normalized"],
                "corpus_db_path": p["active_db"],
                "runtime_settings": {"model": "gpt-test", "max_output_tokens": 1000},
            },
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {"action": "read_active_semantic_release", "corpus_db_path": _resolved(p["active_db"])},
                ),
                (
                    "normalizer",
                    {
                        "action": "normalize_document",
                        "structured_path": _resolved(p["normalizer_structured"]),
                        "normalized_output_path": _resolved(p["expected_normalized"]),
                        "runtime_settings": {"model": "gpt-test", "max_output_tokens": 1000},
                        "release": _active_release_payload(),
                    },
                ),
            ],
        ),
        GoldenCase(
            "normalizer.healthcheck",
            lambda _p: {"runtime_settings": {"model": "gpt-test", "max_output_tokens": 1024}},
            product_calls=lambda _p: [
                (
                    "normalizer",
                    {
                        "action": "healthcheck",
                        "runtime_settings": {"model": "gpt-test", "max_output_tokens": 1024},
                    },
                )
            ],
        ),
    ]


def _resolved(value: str) -> str:
    return str(Path(value).expanduser().resolve())
