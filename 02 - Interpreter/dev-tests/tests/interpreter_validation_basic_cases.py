from __future__ import annotations

import pytest

from llm_interpreter.interpreter import _validate_request
from llm_interpreter.providers import ProviderError
from .interpreter_validation_support import clone_request


def test_accepts_valid_request(sample_request):
    pages = _validate_request(sample_request)
    assert len(pages) == 2
    assert pages[0]["page"] == 1


def test_rejects_missing_source_name(sample_request):
    request = clone_request(sample_request)
    request["source"]["file_name"] = ""
    with pytest.raises(ProviderError, match="source.file_name"):
        _validate_request(request)


def test_rejects_page_count_mismatch(sample_request):
    request = clone_request(sample_request)
    request["source"]["page_count"] = 3
    with pytest.raises(ProviderError, match="page_count"):
        _validate_request(request)


def test_rejects_non_integer_page_count(sample_request):
    request = clone_request(sample_request)
    request["source"]["page_count"] = "two"
    with pytest.raises(ProviderError, match="positive Ganzzahl"):
        _validate_request(request)


def test_rejects_out_of_order_pages(sample_request):
    request = clone_request(sample_request)
    request["page_assets"][0]["page"] = 2
    with pytest.raises(ProviderError, match="kanonischer Reihenfolge"):
        _validate_request(request)


def test_rejects_non_object_context(sample_request):
    request = clone_request(sample_request)
    request["context"] = []
    with pytest.raises(ProviderError, match="context muss ein Objekt sein"):
        _validate_request(request)


def test_rejects_legacy_reference_sections(sample_request):
    request = clone_request(sample_request)
    request["ocr_reference"]["sections"] = []
    with pytest.raises(ProviderError, match="Legacy-OCR-Reference nicht erlaubt"):
        _validate_request(request)


def test_rejects_legacy_reference_block_refs(sample_request):
    request = clone_request(sample_request)
    request["ocr_reference"]["block_refs"] = ["page1_para_1"]
    with pytest.raises(ProviderError, match="Legacy-OCR-Reference nicht erlaubt"):
        _validate_request(request)
