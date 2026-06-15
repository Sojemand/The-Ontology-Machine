from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import call_tool
from mcp_server.tool_visibility import kernel_syscall_context


def test_sample_set_review_aggregates_recurring_fields_and_keeps_one_off_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    input_paths = [Path("C:/tmp/story1.odt"), Path("C:/tmp/story2.odt"), Path("C:/tmp/story3.odt")]

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
                        "projections": [{"projection_id": "fantasy.story.default.v1", "label": "Fantasy Story"}],
                    }
                },
            }
        if module_key == "orchestrator":
            path = payload["source_document_path"]
            rare = ["Rare Artifact"] if path.endswith("3.odt") else []
            return {
                "status": "ok",
                "source_document_path": path,
                "signals": {"filename": Path(path).name, "extension": ".odt", "estimated_document_type": "story"},
                "content_hints": {
                    "headings": [],
                    "field_like_phrases": ["household roles", "product categories", *rare],
                    "candidate_markers": ["parents", "nanny", "mixes"],
                },
                "excerpt": {
                    "chunks": [
                        "My parents and the nanny were part of the household. "
                        "The business sold breakfast mixes."
                    ]
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
            {},
        )

    coverage = result["taxonomy_coverage"]
    recurring = " ".join(item["label"] for item in coverage["recurring_field_candidates"])
    one_off = " ".join(item["label"] for item in coverage["one_off_field_candidates"])

    assert result["question_contract"] == "document_set_release_refinement"
    assert "household roles" in recurring
    assert "product categories" in recurring
    assert "Rare Artifact" in one_off
    assert "Rare Artifact" not in recurring
    assert coverage["requires_agent_field_proposal"] is True
    assert "household roles" in " ".join(coverage["observed_content_evidence"]["field_like_or_heading_phrases"])
    assert "One-off field candidates" in " ".join(result["sample_set"]["warnings"])
