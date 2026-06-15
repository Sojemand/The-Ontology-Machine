from __future__ import annotations

import pytest

from normalizer_vision.document_io import DocumentIoValidationError
from normalizer_vision.models import load_config
from normalizer_vision.normalizer import DocumentNormalizer
from normalizer_vision.normalizer.batch_workflow import _collect_batch_files
from normalizer_vision.providers import ProviderError


def test_normalizer_build_prompt_preview_rejects_oversize_structured_file(tmp_project_root, sample_structured_file, mock_provider):
    config = load_config(tmp_project_root)
    config.max_structured_bytes = 32
    normalizer = DocumentNormalizer(tmp_project_root, config, provider=mock_provider)

    with pytest.raises(DocumentIoValidationError, match="max_structured_bytes"):
        normalizer.build_prompt_preview(sample_structured_file)


def test_normalizer_batch_rejects_product_limits(tmp_project_root, sample_batch_dir, mock_provider, normalizer_runtime_settings):
    config = load_config(tmp_project_root)
    config.max_batch_files = 1
    config.max_batch_workers = 1
    normalizer = DocumentNormalizer(tmp_project_root, config, runtime_settings=normalizer_runtime_settings, provider=mock_provider)

    with pytest.raises(ValueError, match="max_batch_files"):
        normalizer.normalize_batch(sample_batch_dir, tmp_project_root / "output", workers=1)
    with pytest.raises(ValueError, match="max_batch_workers"):
        normalizer.normalize_batch(sample_batch_dir, tmp_project_root / "output", workers=2)


def test_normalizer_batch_stops_after_systemic_provider_error(
    tmp_project_root,
    sample_batch_dir,
    normalizer_runtime_settings,
):
    class SystemicAuthFailureProvider:
        provider_name = "openai"

        def generate(self, **_kwargs):
            raise ProviderError("Provider API Fehler 401: unauthorized", status_code=401)

        def is_available(self):
            return True

    config = load_config(tmp_project_root)
    config.max_batch_files = 10
    normalizer = DocumentNormalizer(
        tmp_project_root,
        config,
        runtime_settings=normalizer_runtime_settings,
        provider=SystemicAuthFailureProvider(),
    )

    results = normalizer.normalize_batch(sample_batch_dir, tmp_project_root / "output", workers=1)

    assert len(results) == 1
    assert results[0].status == "ERROR"
    assert results[0].review_reason == "batch_fail_fast"
    assert "Batch abgebrochen" in results[0].message
    assert "1 Dateien nicht gestartet" in results[0].message


def test_collect_batch_files_rejects_limit_while_iterating(tmp_path):
    batch_dir = tmp_path / "batch"
    batch_dir.mkdir()
    for index in range(3):
        (batch_dir / f"sample_{index}.structured.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="max_batch_files"):
        _collect_batch_files(batch_dir, 2)
