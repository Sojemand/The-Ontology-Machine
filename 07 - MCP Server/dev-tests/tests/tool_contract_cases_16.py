from __future__ import annotations

from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "inspect_pipeline_product_context",
            lambda p: {"max_workflows": 5},
        ),
        GoldenCase(
            "explain_pipeline_capabilities",
            lambda p: {"question": "Was kann ich alles mit der Datenbank tun?"},
        ),
        GoldenCase(
            "recommend_pipeline_next_steps",
            lambda p: {"goal": "Ich habe mehrere neue Dokumente und will die Datenbank darauf schaerfen."},
        ),
        GoldenCase(
            "review_source_sample_set_taxonomy_coverage",
            lambda p: {
                "corpus_db_path": p["active_db"],
                "max_excerpt_chars": 5000,
            },
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {"action": "read_active_semantic_release", "corpus_db_path": p["active_db"]},
                ),
                (
                    "orchestrator",
                    {
                        "action": "inspect_source_document_sample",
                        "source_document_path": p["run_input"] + "\\story.txt",
                        "max_excerpt_chars": 5000,
                    },
                ),
            ],
        ),
        GoldenCase(
            "prepare_source_samples_for_input",
            lambda p: {"source_document_paths": [p["sample_document"]], "user_confirmed": True},
        ),
    ]
