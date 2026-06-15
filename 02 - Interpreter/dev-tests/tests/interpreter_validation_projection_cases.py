from __future__ import annotations

import pytest

from llm_interpreter.interpreter import _validate_request
from llm_interpreter.providers import ProviderError
from .interpreter_validation_support import clone_request


def test_rejects_missing_projection_catalog(sample_request):
    request = clone_request(sample_request)
    request.pop("projection_catalog", None)

    with pytest.raises(ProviderError, match="projection_catalog fehlt"):
        _validate_request(request)


def test_rejects_invalid_projection_catalog_shape(sample_request):
    request = clone_request(sample_request)
    request["projection_catalog"] = {"catalog_version": "v1", "projections": []}

    with pytest.raises(ProviderError, match="projection_catalog"):
        _validate_request(request)


def test_accepts_projection_catalog_with_additive_release_metadata(sample_request, sample_projection_catalog):
    request = clone_request(sample_request)
    request["projection_catalog"] = {
        **sample_projection_catalog,
        "release_id": "semantic_release.default",
        "release_version": "2026-03-28.v6",
        "release_fingerprint": "sha256:semantic-default",
        "master_taxonomy_id": "vision_taxonomy",
        "master_taxonomy_release_id": "sha256:master-line",
        "runtime_locale": "en",
    }

    pages = _validate_request(request)

    assert len(pages) == 2


def test_rejects_projection_catalog_with_non_canonical_runtime_locale(sample_request, sample_projection_catalog):
    request = clone_request(sample_request)
    request["projection_catalog"] = {**sample_projection_catalog, "runtime_locale": "de"}

    with pytest.raises(ProviderError, match="projection_catalog"):
        _validate_request(request)


def test_accepts_real_projection_catalog_with_locale_metadata_from_normalizer(sample_request, locale_runtime_payload_en):
    request = clone_request(sample_request)
    request["projection_catalog"] = locale_runtime_payload_en["projection_catalog"]

    pages = _validate_request(request)

    assert len(pages) == 2
    assert request["projection_catalog"]["runtime_locale"] == "en"
    assert request["projection_catalog"]["master_taxonomy_release_id"].startswith("sha256:")
