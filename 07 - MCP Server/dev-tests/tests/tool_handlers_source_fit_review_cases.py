from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import call_tool
from mcp_server.tool_visibility import kernel_syscall_context


def test_active_input_sample_review_filters_processing_metadata_and_does_not_invent_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    input_paths = [Path("C:/tmp/Fantasy Story 3.odt")]

    def fake_active_paths(_arguments: dict[str, Any]) -> list[Path]:
        return input_paths

    def fake_invoke(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        if module_key == "corpus_builder":
            return {
                "status": "ok",
                "detail": {
                    "release": {
                        "release_id": "fantasy.story.default",
                        "projection_ids": ["fantasy.story.default.v1"],
                        "projections": [
                            {
                                "projection_id": "fantasy.story.default.v1",
                                "label": "Fantasy Story",
                                "routing": {"when_to_use": "narrative fantasy stories"},
                            }
                        ],
                    }
                },
            }
        if module_key == "orchestrator":
            return {
                "status": "ok",
                "source_document_path": payload["source_document_path"],
                "sample_label": "Fantasy Story 3",
                "signals": {
                    "filename": "Fantasy Story 3.odt",
                    "extension": ".odt",
                    "optimizer_profile": "vision",
                    "vision_mode": "vision_grouped_sections",
                    "estimated_document_type": "story",
                },
                "content_hints": {
                    "headings": [],
                    "field_like_phrases": ["mode: vision", "prompt_strategy: vision_grouped_sections", "section_count: 3"],
                    "candidate_markers": ["they", "blondie", "then", "parents", "mixes"],
                },
                "excerpt": {
                    "chars_returned": 210,
                    "truncated": False,
                    "chunks": [
                        "My parents had Blondie and Susan around the house, plus a nanny. "
                        "Their business sold breakfast mixes and other lifestyle products."
                    ],
                },
            }
        raise AssertionError(module_key)

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)
    monkeypatch.setattr(
        "mcp_server.tool_handler_source_sample_set_review.active_input_folder_sample_paths",
        fake_active_paths,
    )

    with kernel_syscall_context():
        result = call_tool(
            "review_source_sample_set_taxonomy_coverage",
            {"corpus_db_path": "C:/tmp/Fantasy.db"},
        )

    coverage = result["taxonomy_coverage"]
    fields = coverage["recurring_field_candidates"]
    markers = [item["label"] for item in coverage["recurring_routing_markers"]]
    joined_fields = " ".join(item["label"] for item in fields).casefold()
    joined_markers = " ".join(markers).casefold()

    assert "mode" not in joined_fields
    assert "prompt_strategy" not in joined_fields
    assert "section_count" not in joined_fields
    assert "vision" not in joined_markers
    assert "they" not in markers
    assert "then" not in markers
    assert fields == []
    assert "parents" in markers
    assert "mixes" in markers
    assert coverage["requires_agent_field_proposal"] is False
    assert result["sample_set"]["sample_summaries"][0]["content_hints"]["ignored_technical_hints"] == [
        "mode: vision",
        "prompt_strategy: vision_grouped_sections",
        "section_count: 3",
    ]
