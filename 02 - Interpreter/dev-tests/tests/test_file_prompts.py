"""Tests for file-profile OCR guideline budgeting and section coverage."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from llm_interpreter.models import InterpreterConfig
from llm_interpreter.prompts.workflow import build_user_prompt_text, build_vision_messages


def _as_born_digital(sample_request: dict) -> dict:
    request = copy.deepcopy(sample_request)
    request["source"]["file_name"] = "terms.pdf"
    request["source"]["file_path"] = "terms.pdf"
    request["source"]["is_scan"] = False
    return request


def _file_config(**overrides) -> InterpreterConfig:
    return InterpreterConfig(interpreter_profile="file", **overrides)


def test_file_prompt_includes_tail_sections_with_default_limits(sample_request):
    request = _as_born_digital(sample_request)
    request["ocr_reference"]["blocks"] = [
        {
            "id": f"page1_para_{index}",
            "type": "paragraph",
            "value": f"Section {index:02d} carry-forward body",
            "value_type": "text",
            "position": {"page": 1, "paragraph_index": index},
        }
        for index in range(1, 26)
    ]

    prompt = build_user_prompt_text(request, _file_config())

    assert "Section 01 carry-forward body" in prompt
    assert "Section 25 carry-forward body" in prompt


def test_file_prompt_renders_all_raw_blocks_without_guideline_budgeting(sample_request):
    request = _as_born_digital(sample_request)
    request["ocr_reference"]["blocks"] = [
        {"id": "sec_a", "type": "paragraph", "value": "A" * 20, "value_type": "text", "position": {"page": 1, "paragraph_index": 1}},
        {"id": "sec_b", "type": "paragraph", "value": "B" * 20, "value_type": "text", "position": {"page": 1, "paragraph_index": 2}},
        {"id": "sec_c", "type": "paragraph", "value": "C" * 20, "value_type": "text", "position": {"page": 1, "paragraph_index": 3}},
    ]

    prompt = build_user_prompt_text(request, _file_config())

    assert "OCR raw blocks in source order:" in prompt
    assert "AAAAAAAAAAAAAAAAAAAA" in prompt
    assert "BBBBBBBBBBBBBBBBBBBB" in prompt
    assert "CCCCCCCCCCCCCCCCCCCC" in prompt


def test_born_digital_prompt_uses_raw_first_and_small_summary_rules(sample_request):
    request = _as_born_digital(sample_request)
    messages = build_vision_messages(request, _file_config())
    prompt = messages[1]["content"][0]["text"]
    system_prompt = messages[0]["content"]

    assert "raw/page-scoped reference as the primary source" in system_prompt
    assert "the visible column structure overrides raw block order" in system_prompt
    assert "return a compact high-signal extraction, set needs_review=true" in system_prompt
    assert "Split raw sections into separate segments when the local semantic act changes" in prompt
    assert "Raw section order is not authoritative on multi-column pages" in prompt
    assert "mention column-mixed raw order in review_reason" in prompt
    assert "content.free_text is an optional short keyword summary" in system_prompt
    assert "Do NOT reproduce the full visible text in content.free_text" in system_prompt
    assert "Split segments at clear local boundaries such as speaker change, question followed by answer" in system_prompt
    assert "Do not keep question and answer in the same segment." in system_prompt
    assert "function is optional but preferred when it adds clear local semantic meaning or clause purpose." in system_prompt
    assert "Single Source of Truth" not in system_prompt


def test_scan_prompt_keeps_image_first_and_full_free_text_rules(sample_request):
    messages = build_vision_messages(sample_request, InterpreterConfig())
    prompt = messages[1]["content"][0]["text"]
    system_prompt = messages[0]["content"]

    assert "Read the provided page images yourself first." in system_prompt
    assert "content.free_text is a corrected full text produced by you in reading order." in system_prompt
    assert "Single Source of Truth" in system_prompt
    assert "OCR raw blocks in source order:" in prompt


def test_file_messages_keep_image_for_born_digital_request(sample_request):
    request = _as_born_digital(sample_request)
    page_assets = [
        {
            "page": 1,
            "path": Path("page_001.png"),
            "media_type": "image/png",
            "bytes": b"\x89PNG\r\n\x1a\n" + b"a" * 1024,
        }
    ]

    messages = build_vision_messages(
        request,
        _file_config(),
        page_assets=page_assets,
    )

    assert [block["type"] for block in messages[1]["content"]] == ["text", "input_image"]


def test_file_messages_keep_large_image_for_born_digital_request(sample_request):
    request = _as_born_digital(sample_request)
    page_assets = [
        {
            "page": 1,
            "path": Path("page_001.png"),
            "media_type": "image/png",
            "bytes": b"\x89PNG\r\n\x1a\n" + b"a" * 140000,
        }
    ]

    messages = build_vision_messages(
        request,
        _file_config(),
        page_assets=page_assets,
    )

    assert [block["type"] for block in messages[1]["content"]] == ["text", "input_image"]
