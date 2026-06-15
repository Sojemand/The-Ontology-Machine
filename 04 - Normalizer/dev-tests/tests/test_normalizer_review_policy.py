from __future__ import annotations

import json
from pathlib import Path

from normalizer_vision.models import load_config
from normalizer_vision.normalizer import DocumentNormalizer


def _normalized_output_path(project_root: Path, structured_path: Path) -> Path:
    return project_root / "output" / structured_path.name.replace(".structured.json", ".structured.normalized.json")


def test_normalize_marks_review_for_problematic_notes(tmp_project_root, sample_structured_file, sample_model_output, normalizer_runtime_settings):
    problematic_output = json.loads(json.dumps(sample_model_output))
    problematic_output["context"]["normalization_notes"] = ["Unsicheres Mapping im Tabellenbereich."]
    problematic_output["content"]["fields"]["mystery_field"] = "unexpected"

    class ProblemProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(problematic_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=ProblemProvider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["processing"]["needs_review"] is True
    assert any("Dropped unknown field codes" in note for note in output_data["context"]["normalization_notes"])


def test_normalize_marks_review_for_review_reason_and_other_classification(tmp_project_root, sample_structured_file, sample_model_output, normalizer_runtime_settings):
    review_output = json.loads(json.dumps(sample_model_output))
    review_output["processing"]["review_reason"] = "Could not determine a precise classification."
    review_output["classification"]["document_type"] = "other"

    class ReviewProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(review_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=ReviewProvider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["processing"]["needs_review"] is True
    assert output_data["processing"]["review_reason"] == "Could not determine a precise classification."
    assert output_data["classification"]["document_type"] == "other"


def test_normalize_derives_review_reason_when_model_flags_review_without_reason(tmp_project_root, sample_structured_file, sample_model_output, normalizer_runtime_settings):
    review_output = json.loads(json.dumps(sample_model_output))
    review_output["processing"]["needs_review"] = True
    review_output["processing"]["review_reason"] = None
    review_output["classification"]["document_type"] = "other"
    review_output["context"]["normalization_notes"] = ["Unsichere fachliche Zuordnung im Dokument."]

    class ReviewFallbackProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(review_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=ReviewFallbackProvider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["processing"]["needs_review"] is True
    assert output_data["processing"]["review_reason"]


def test_normalize_does_not_force_review_for_subcategory_other_alone(tmp_project_root, sample_structured_file, sample_model_output, normalizer_runtime_settings):
    review_output = json.loads(json.dumps(sample_model_output))
    review_output["processing"]["needs_review"] = False
    review_output["processing"]["review_reason"] = None
    review_output["classification"]["subcategory"] = "other"

    class ReviewFallbackProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(review_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=ReviewFallbackProvider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["classification"]["subcategory"] == "other"
    assert output_data["processing"]["needs_review"] is False
    assert output_data["processing"]["review_reason"] is None
