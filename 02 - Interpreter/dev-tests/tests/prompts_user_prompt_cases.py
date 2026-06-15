from __future__ import annotations

import copy

import pytest

from llm_interpreter.models import InterpreterConfig
from llm_interpreter.prompts import build_user_prompt_text


class TestBuildUserPrompt:
    def test_uses_raw_blocks_and_projection_catalog(self, sample_request):
        prompt = build_user_prompt_text(sample_request, InterpreterConfig())

        assert "Deterministischer Prompt-View:" not in prompt
        assert f"File: {sample_request['source']['file_name']}" in prompt
        assert f"Type hint: {sample_request['source']['document_type']}" in prompt
        assert f"Source language: {sample_request['source']['language']}" in prompt
        assert "OCR raw blocks in source order:" in prompt
        assert "Beitragsrechnung 2026" in prompt
        assert "Rechnungsnummer RE-2026-001" in prompt
        assert '"layout_label": "header"' in prompt
        assert '"type": "cell"' in prompt

    def test_contains_flexible_key_instruction(self, sample_request):
        prompt = build_user_prompt_text(sample_request, InterpreterConfig())
        assert "Additional fields are allowed only in context, content.fields, and row objects." in prompt
        assert "content.free_text must be corrected full text" in prompt
        assert '"projection_hint": {"projection_id": "finance.default.v1"' in prompt
        assert "Example without hint:" in prompt

    def test_includes_projection_catalog_and_schema_example(self, sample_request, sample_projection_catalog):
        request = copy.deepcopy(sample_request)
        request["projection_catalog"] = sample_projection_catalog

        prompt = build_user_prompt_text(request, InterpreterConfig())
        lines = [line for line in prompt.splitlines() if line.startswith("projection_id=")]

        assert "Projection routing catalog. Choose exactly one projection_id" in prompt
        assert len(lines) == 9
        assert any("projection_id=finance.default.v1 | label=Finance Default v1" in line for line in lines)
        assert any("projection_id=community.spiritual.default.v1 | label=Community Spiritual Default v1" in line for line in lines)
        assert any("example_document_types=membership_record, statement, schedule, general_letter, certificate" in line for line in lines)
        assert "Projection hint rules:" in prompt
        assert '"interpreter_profile"' in prompt
        assert '"additionalProperties": false' in prompt

    def test_accepts_release_metadata_without_rendering_them(self, sample_request, sample_projection_catalog):
        request = copy.deepcopy(sample_request)
        request["projection_catalog"] = {
            **sample_projection_catalog,
            "release_id": "semantic_release.default",
            "release_version": "2026-03-28.v6",
            "release_fingerprint": "sha256:semantic-default",
            "master_taxonomy_id": "vision_taxonomy",
            "master_taxonomy_release_id": "sha256:master-line",
            "runtime_locale": "en",
        }

        prompt = build_user_prompt_text(request, InterpreterConfig())

        assert "Control locale: en." in prompt
        assert "semantic_release.default" not in prompt
        assert "2026-03-28.v6" not in prompt
        assert "sha256:semantic-default" not in prompt
        assert "vision_taxonomy" not in prompt
        assert "sha256:master-line" not in prompt
        assert "runtime_locale" not in prompt

    def test_real_projection_catalog_release_metadata_stays_prompt_inert(
        self,
        sample_request,
        locale_runtime_payload_en,
    ):
        request = copy.deepcopy(sample_request)
        request["projection_catalog"] = locale_runtime_payload_en["projection_catalog"]
        request["source"]["language"] = "fr"

        prompt = build_user_prompt_text(request, InterpreterConfig())

        assert "Control locale: en." in prompt
        assert "Map semantic classification labels, routing decisions" in prompt
        assert locale_runtime_payload_en["projection_catalog"]["release_id"] not in prompt
        assert locale_runtime_payload_en["projection_catalog"]["release_version"] not in prompt
        assert locale_runtime_payload_en["projection_catalog"]["release_fingerprint"] not in prompt
        assert locale_runtime_payload_en["projection_catalog"]["master_taxonomy_release_id"] not in prompt
        assert "runtime_locale" not in prompt

    def test_guideline_honors_visible_prompt_limits(self, sample_request):
        prompt = build_user_prompt_text(sample_request, InterpreterConfig())

        assert "Guideline-Abschnitte:" not in prompt
        assert "Guideline-Facts:" not in prompt
        assert "Guideline-Tabellen:" not in prompt
        assert "120,00 EUR" in prompt

    def test_missing_projection_catalog_fails_closed(self, sample_request):
        request = copy.deepcopy(sample_request)
        request.pop("projection_catalog", None)

        with pytest.raises(ValueError, match="projection_catalog fehlt"):
            build_user_prompt_text(request, InterpreterConfig())
