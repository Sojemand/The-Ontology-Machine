from __future__ import annotations

from llm_interpreter.prompts import SYSTEM_PROMPT


class TestSystemPrompt:
    def test_contains_vision_first_rules(self):
        assert "Read the provided page images yourself first." in SYSTEM_PROMPT
        assert "_source_refs" not in SYSTEM_PROMPT
        assert "content.free_text is a corrected full text produced by you in reading order." in SYSTEM_PROMPT
        assert "OCR raw blocks" in SYSTEM_PROMPT
        assert "projection routing catalog" in SYSTEM_PROMPT.lower()

    def test_avoids_kleingarten_hint_and_keeps_historic_hint(self):
        normalized = SYSTEM_PROMPT.lower()
        assert "kleingartenverein" not in normalized
        assert "modern or historical" in normalized
