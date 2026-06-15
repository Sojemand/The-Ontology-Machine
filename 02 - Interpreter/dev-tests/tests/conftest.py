"""Shared fixtures for the vision interpreter tests."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from tests.support.sample_data import (
    build_sample_llm_output,
    build_sample_projection_catalog,
    build_sample_request,
)


@pytest.fixture
def sample_request(tmp_path) -> dict:
    return build_sample_request(tmp_path)


@pytest.fixture
def sample_request_file(tmp_path, sample_request) -> Path:
    path = tmp_path / "requests" / "scan.request.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sample_request), encoding="utf-8")
    return path


@pytest.fixture
def sample_llm_output() -> dict:
    return build_sample_llm_output()


@pytest.fixture
def sample_projection_catalog() -> dict:
    return build_sample_projection_catalog()


@pytest.fixture(scope="session")
def _locale_runtime_payload_en(tmp_path_factory) -> dict:
    pipeline_root = Path(__file__).resolve().parents[3]
    if str(pipeline_root) not in sys.path:
        sys.path.insert(0, str(pipeline_root))

    from tools.phase4_locale_test_support import build_locale_runtime_artifacts

    _project_root, _release, runtime_payload = build_locale_runtime_artifacts(
        tmp_path_factory.mktemp("normalizer_locale_en"),
        runtime_locale="en",
    )
    return runtime_payload


@pytest.fixture
def locale_runtime_payload_en(_locale_runtime_payload_en) -> dict:
    return copy.deepcopy(_locale_runtime_payload_en)
