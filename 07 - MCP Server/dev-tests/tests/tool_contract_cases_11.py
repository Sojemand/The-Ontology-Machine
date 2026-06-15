from __future__ import annotations

from pathlib import Path

from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "optimizer.classify_document",
            lambda p: {
                "source_path": p["sample_document"],
                "input_root": str(Path(p["sample_document"]).parent),
            },
            product_calls=lambda p: [
                (
                    "optimizer",
                    {
                        "action": "classify_document",
                        "source_path": _resolved(p["sample_document"]),
                        "input_root": _resolved(str(Path(p["sample_document"]).parent)),
                    },
                )
            ],
        ),
        GoldenCase(
            "optimizer.extract_document",
            lambda p: {
                "source_path": p["sample_document"],
                "input_root": str(Path(p["sample_document"]).parent),
                "output_root": str(Path(p["raw_dir"]).parent),
                "raw_output_path": str(Path(p["raw_dir"]) / "Fantasy_Story.raw.json"),
                "page_images_dir": str(Path(p["raw_dir"]).parent / "page_images" / "Fantasy_Story"),
                "logical_source_path": "samples/Fantasy Story.txt",
                "optimizer_profile": "file",
            },
            product_calls=lambda p: [
                (
                    "optimizer",
                    {
                        "action": "extract_document",
                        "source_path": _resolved(p["sample_document"]),
                        "input_root": _resolved(str(Path(p["sample_document"]).parent)),
                        "output_root": _resolved(str(Path(p["raw_dir"]).parent)),
                        "raw_output_path": _resolved(str(Path(p["raw_dir"]) / "Fantasy_Story.raw.json")),
                        "page_images_dir": _resolved(str(Path(p["raw_dir"]).parent / "page_images" / "Fantasy_Story")),
                        "logical_source_path": "samples/Fantasy Story.txt",
                        "optimizer_profile": "file",
                    },
                )
            ],
        ),
        GoldenCase(
            "optimizer.healthcheck",
            lambda _p: {"optimizer_profile": "vision", "required_dependencies": ["pdf-pdfplumber"]},
            product_calls=lambda _p: [
                (
                    "optimizer",
                    {
                        "action": "healthcheck",
                        "optimizer_profile": "vision",
                        "required_dependencies": ["pdf-pdfplumber"],
                    },
                )
            ],
        ),
        GoldenCase(
            "optimizer.scan_debug_input",
            lambda p: {
                "input_root": p["run_input"],
                "debug_root": p["debug_root"],
                "session_root": str(Path(p["debug_root"]) / "scan-session"),
                "filters": {"format": ".txt", "batch_size": 1},
                "hash_tools": {"use_processed_hashes": True},
            },
            product_calls=lambda p: [
                (
                    "optimizer",
                    {
                        "action": "scan_debug_input",
                        "input_root": _resolved(p["run_input"]),
                        "session_root": _resolved(str(Path(p["debug_root"]) / "scan-session")),
                        "mode": "scan",
                        "filters": {"format": ".txt", "batch_size": 1},
                        "hash_tools": {"use_processed_hashes": True},
                    },
                )
            ],
        ),
        GoldenCase(
            "optimizer.describe_surfaces",
            lambda _p: {},
            edit_calls=lambda _p: [("optimizer", {"action": "describe_surfaces"})],
        ),
        GoldenCase(
            "optimizer.read_surface",
            lambda _p: {"surface_id": "optimizer.settings"},
            edit_calls=lambda _p: [("optimizer", {"action": "read_surface", "surface_id": "optimizer.settings"})],
        ),
        GoldenCase(
            "optimizer.validate_surface",
            lambda _p: {"surface_id": "optimizer.signature_overrides", "value": {"version": 1, "overrides": {}}},
            edit_calls=lambda _p: [
                (
                    "optimizer",
                    {
                        "action": "validate_surface",
                        "surface_id": "optimizer.signature_overrides",
                        "value": {"version": 1, "overrides": {}},
                    },
                )
            ],
        ),
        GoldenCase(
            "optimizer.write_surface",
            lambda _p: {"surface_id": "optimizer.signature_overrides", "value": {"version": 1, "overrides": {}}},
            edit_calls=lambda _p: [
                (
                    "optimizer",
                    {
                        "action": "write_surface",
                        "surface_id": "optimizer.signature_overrides",
                        "value": {"version": 1, "overrides": {}},
                    },
                )
            ],
        ),
        GoldenCase(
            "corpus_builder.load_document",
            lambda p: {
                "artifact_root": p["artifact_root"],
                "normalized_path": p["normalized_artifact"],
                "structured_path": p["structured_artifact"],
                "validation_path": p["validation_artifact"],
                "raw_path": p["raw_artifact"],
                "corpus_db_path": p["active_db"],
                "corpus_output_folder": p["corpus_root"],
                "persist_page_images_in_db": False,
                "page_images_dir": p["page_images_dir"],
            },
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {
                        "action": "load_document",
                        "corpus_db_path": _resolved(p["active_db"]),
                        "normalized_path": _resolved(p["normalized_artifact"]),
                        "structured_path": _resolved(p["structured_artifact"]),
                        "validation_path": _resolved(p["validation_artifact"]),
                        "raw_path": _resolved(p["raw_artifact"]),
                        "persist_page_images_in_db": False,
                        "page_images_dir": _resolved(p["page_images_dir"]),
                    },
                )
            ],
        ),
        GoldenCase(
            "corpus_builder.healthcheck",
            lambda _p: {"runtime_model": "text-embedding-3-small", "scope": "pipeline_run"},
            product_calls=lambda _p: [
                (
                    "corpus_builder",
                    {
                        "action": "healthcheck",
                        "runtime_settings": {"model": "text-embedding-3-small"},
                        "scope": "pipeline_run",
                    },
                )
            ],
        ),
        GoldenCase(
            "corpus_builder.scan_debug_input",
            lambda p: {
                "input_root": p["artifact_root"],
                "debug_root": p["debug_root"],
                "session_root": str(Path(p["debug_root"]) / "corpus-scan-session"),
            },
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {
                        "action": "scan_debug_input",
                        "input_root": _resolved(p["artifact_root"]),
                        "session_root": _resolved(str(Path(p["debug_root"]) / "corpus-scan-session")),
                        "mode": "scan",
                    },
                )
            ],
        ),
    ]


def _resolved(value: str) -> str:
    return str(Path(value).expanduser().resolve())
