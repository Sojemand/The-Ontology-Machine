from __future__ import annotations

import json
from pathlib import Path

import pytest

from normalizer_vision.normalizer import DocumentNormalizer
from tests.fixtures.normalizer_cases import operations_config, operations_output


def _normalized_output_path(project_root: Path, structured_path: Path) -> Path:
    return project_root / "output" / structured_path.name.replace(".structured.json", ".structured.normalized.json")


OPERATIONS_CASES = [
    (
        operations_output(
            document_type="delivery_note",
            category="operations",
            subcategory="logistics",
            document_title="Transport order / delivery note",
            description="Transport for multiple machines.",
            fields={"document_number": "BK-20220771 - outbound", "our_reference": "aw", "contact_person": "Hr. Rainer Juraske", "loading_address": "Im Taubenfeld 5", "unloading_address": "Moellensdorfer Str. 13"},
            rows=[{"_row_type": "line_item", "position": 1, "quantity": "4", "description": "Euro pallets with tools"}],
        ),
        ["document_number", "our_reference", "contact_person", "loading_address", "unloading_address"],
        ["position", "quantity", "description"],
        False,
    ),
    (
        operations_output(
            document_type="report",
            category="operations",
            subcategory="execution_plan",
            document_title="Equipment replacement 121C-179C execution plan",
            description="Execution plan for the replacement.",
            fields={"subject": "Equipment replacement 121C-179C execution plan"},
            rows=[{"_row_type": "timeline_entry", "scheduled_date": "2026-06-27", "description": "Set up 500-ton crane", "section": "NH3-I"}],
        ),
        ["subject"],
        ["scheduled_date", "description", "section"],
        False,
    ),
    (
        operations_output(
            document_type="other",
            category="operations",
            subcategory="travel_instruction",
            document_title="Travel instructions to GR 2017 in Piesteritz",
            description="Travel instructions for the site.",
            fields={"subject": "Travel instructions to GR 2017 in Piesteritz"},
            rows=[],
        ),
        ["subject"],
        [],
        True,
    ),
]


@pytest.mark.parametrize(("output_json", "expected_form_fields", "expected_columns", "expected_needs_review"), OPERATIONS_CASES)
def test_normalize_operations_profile_regressions(
    tmp_project_root,
    sample_structured_file,
    output_json,
    expected_form_fields,
    expected_columns,
    expected_needs_review,
    normalizer_runtime_settings,
):
    class Provider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(output_json)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        operations_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=Provider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["processing"]["needs_review"] is expected_needs_review
    assert output_data["context"]["taxonomy_profile_id"] == "operations.default.v1"
    assert output_data["content"]["structure"]["form_fields"] == expected_form_fields
    assert output_data["content"]["structure"]["columns"] == expected_columns


def test_normalize_operations_profile_splits_list_rows_into_scalar_entries(
    tmp_project_root,
    sample_structured_file,
    normalizer_runtime_settings,
):
    exploded_output = operations_output(
        document_type="report",
        category="operations",
        subcategory="execution_plan",
        document_title="Equipment replacement 121C-179C execution plan",
        description="Execution plan with multiple steps per date.",
        fields={"subject": "Equipment replacement 121C-179C execution plan"},
        rows=[{"_row_type": "timeline_entry", "scheduled_date": "2026-06-27", "description": ["Set up 500-ton crane before 121-C/179-C NH3-I", "Dismantle 121-C/179-C"], "section": "NH3-I"}],
    )

    class Provider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(exploded_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        operations_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=Provider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["content"]["structure"]["columns"] == ["scheduled_date", "description", "section"]
    assert output_data["content"]["rows"] == [
        {"_row_type": "timeline_entry", "_row_index": 0, "scheduled_date": "2026-06-27", "description": "Set up 500-ton crane before 121-C/179-C NH3-I", "section": "NH3-I"},
        {"_row_type": "timeline_entry", "_row_index": 1, "scheduled_date": "2026-06-27", "description": "Dismantle 121-C/179-C", "section": "NH3-I"},
    ]
