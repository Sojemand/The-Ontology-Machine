from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.workflows.llm_calls.function_registry import get_llm_function_definition
from semantic_control_kernel.workflows.llm_calls.report_validation import normalize_report_output, validate_report_output


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_valid_sample_reports_pass() -> None:
    fixtures = _fixtures()

    sample = validate_report_output(
        report_text=fixtures["valid_user_report_samples"],
        definition=get_llm_function_definition("user_report_samples"),
    )

    assert sample.passed


def test_reports_reject_json_metadata_bad_headings_implementation_terms_and_mutation_claims() -> None:
    definition = get_llm_function_definition("user_report_samples")

    assert not validate_report_output(report_text='{"schema_version":"x"}', definition=definition).passed
    assert not validate_report_output(report_text="---\ntitle: x\n---\n# Sample Analysis Report", definition=definition).passed
    assert not validate_report_output(report_text=_fixtures()["invalid_report_heading"], definition=definition).passed
    assert not validate_report_output(
        report_text=_fixtures()["valid_user_report_samples"] + "\nInternal function analyze_samples was used.",
        definition=definition,
    ).passed
    assert not validate_report_output(
        report_text=_fixtures()["valid_user_report_samples"] + "\nThe schema version is kernel.sample_analyses.v1.",
        definition=definition,
    ).passed
    assert not validate_report_output(
        report_text=_fixtures()["valid_user_report_samples"] + "\nThe user_report_samples function created this report.",
        definition=definition,
    ).passed
    assert not validate_report_output(
        report_text=_fixtures()["valid_user_report_samples"] + "\nThe taxonomy was changed.",
        definition=definition,
    ).passed


def test_report_validation_accepts_common_markdown_json_wrapper() -> None:
    definition = get_llm_function_definition("user_report_samples")
    wrapped = json.dumps({"report": _fixtures()["valid_user_report_samples"]})

    report = validate_report_output(report_text=wrapped, definition=definition)

    assert report.passed
    assert normalize_report_output(wrapped).startswith("# Sample Analysis Report")
