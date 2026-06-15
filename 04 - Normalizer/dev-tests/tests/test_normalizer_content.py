from __future__ import annotations

import json
from pathlib import Path

from normalizer_vision.models import load_config
from normalizer_vision.normalizer import DocumentNormalizer


def _normalized_output_path(project_root: Path, structured_path: Path) -> Path:
    return project_root / "output" / structured_path.name.replace(".structured.json", ".structured.normalized.json")


def test_normalize_context_falls_back_to_raw_lists_and_total_when_model_omits_values(
    tmp_project_root,
    sample_structured_file,
    sample_model_output,
    normalizer_runtime_settings,
):
    raw_payload = json.loads(sample_structured_file.read_text(encoding="utf-8"))
    raw_payload["context"].update(
        {
            "tags": ["raw-tag", "raw-tag", "raw-only"],
            "people": ["Raw Person"],
            "organizations": ["Raw Org"],
            "locations": ["Raw Address"],
            "currencies": ["EUR", "EUR"],
            "total_monetary_value": 987.65,
        }
    )
    sample_structured_file.write_text(json.dumps(raw_payload), encoding="utf-8")
    fallback_output = json.loads(json.dumps(sample_model_output))
    fallback_output["context"].update({"tags": [], "people": {"unexpected": "shape"}, "organizations": None, "locations": "", "currencies": [], "total_monetary_value": None})

    class FallbackProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(fallback_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=FallbackProvider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["context"]["tags"] == ["raw-tag", "raw-only"]
    assert output_data["context"]["people"] == ["Raw Person"]
    assert output_data["context"]["organizations"] == ["Raw Org"]
    assert output_data["context"]["locations"] == ["Raw Address"]
    assert output_data["context"]["currencies"] == ["EUR"]
    assert output_data["context"]["total_monetary_value"] == 987.65


def test_normalize_context_prefers_non_empty_model_values_over_raw_context(
    tmp_project_root,
    sample_structured_file,
    sample_model_output,
    normalizer_runtime_settings,
):
    raw_payload = json.loads(sample_structured_file.read_text(encoding="utf-8"))
    raw_payload["context"].update({"tags": ["raw-tag"], "people": ["Raw Person"], "organizations": ["Raw Org"], "locations": ["Raw Address"], "currencies": ["EUR"], "total_monetary_value": 111.0})
    sample_structured_file.write_text(json.dumps(raw_payload), encoding="utf-8")
    override_output = json.loads(json.dumps(sample_model_output))
    override_output["context"].update({"tags": ["model-tag", "model-tag", "model-only"], "people": ["Model Person"], "organizations": ["Model Org"], "locations": ["Model Address"], "currencies": ["CHF", "CHF"], "total_monetary_value": 222.0})

    class OverrideProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(override_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=OverrideProvider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["context"]["tags"] == ["model-tag", "model-only"]
    assert output_data["context"]["people"] == ["Model Person"]
    assert output_data["context"]["organizations"] == ["Model Org"]
    assert output_data["context"]["locations"] == ["Model Address"]
    assert output_data["context"]["currencies"] == ["CHF"]
    assert output_data["context"]["total_monetary_value"] == 222.0


def test_normalize_drops_null_placeholders_from_strict_schema_output(
    tmp_project_root,
    sample_structured_file,
    sample_model_output,
    normalizer_runtime_settings,
):
    strict_like_output = json.loads(json.dumps(sample_model_output))
    strict_like_output["processing"].update({"processed_at": None, "model": None, "provider": None})
    strict_like_output["content"]["fields"].update({"currency": None, "due_date": None, "other": None})
    strict_like_output["content"]["rows"][0].update({"amount_due": None, "amount_paid": None, "balance": None, "other": None})

    class StrictishProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(strict_like_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=StrictishProvider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert "currency" not in output_data["content"]["fields"]
    assert "due_date" not in output_data["content"]["fields"]
    assert "amount_due" not in output_data["content"]["rows"][0]
    assert "_source_refs" not in output_data["content"]["fields"]
    assert "_source_refs" not in output_data["content"]["rows"][0]


def test_normalize_ignores_relations_returned_by_provider(
    tmp_project_root,
    sample_structured_file,
    sample_model_output,
    normalizer_runtime_settings,
):
    relation_output = json.loads(json.dumps(sample_model_output))
    relation_output["relations"] = [
        {"type": "normalized_from", "file_name": "sample.pdf", "content_hash": "sha256:pdfhash"},
        {"type": "related_document", "file_name": "other.pdf", "content_hash": "sha256:otherhash"},
    ]

    class RelationProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(relation_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=RelationProvider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert "relations" not in output_data
