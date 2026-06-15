from __future__ import annotations

import copy

import pytest

from llm_interpreter.interpreter.validation import validate_request
from llm_interpreter.models import InterpreterConfig
from llm_interpreter.providers import ProviderError


@pytest.mark.parametrize("legacy_key", ["pages", "file_reference"])
def test_legacy_top_level_request_shapes_are_rejected(sample_request, legacy_key: str) -> None:
    request = copy.deepcopy(sample_request)
    request[legacy_key] = []

    with pytest.raises(ProviderError, match="Legacy-Request-Shape nicht erlaubt"):
        validate_request(request, InterpreterConfig())
