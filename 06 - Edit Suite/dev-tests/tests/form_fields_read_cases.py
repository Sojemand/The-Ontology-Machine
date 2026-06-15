from __future__ import annotations

from types import SimpleNamespace

from edit_suite.ui.form_fields import read_form_value
from edit_suite.ui.nested_policy_editor import read_value as read_nested_policy_value

from form_fields_support import _Entry, _Textbox, _Var


def test_read_form_value_restores_typed_leaf_map() -> None:
    widget = SimpleNamespace(
        _form_fields={
            "checks.free_text": {"kind": "bool", "widget": object(), "variable": _Var(True)},
            "match.min_string_length": {"kind": "int", "widget": _Entry("4")},
            "match.number_tolerance_absolute": {"kind": "float", "widget": _Entry("0.25")},
            "match.scalar_level": {"kind": "string", "widget": _Entry("WARN")},
            "match.context_fields": {"kind": "list", "widget": _Textbox("company\niban\n\n")},
        }
    )

    assert read_form_value(widget) == {
        "checks.free_text": True,
        "match.min_string_length": 4,
        "match.number_tolerance_absolute": 0.25,
        "match.scalar_level": "WARN",
        "match.context_fields": ["company", "iban"],
    }


def test_read_nested_policy_value_restores_typed_top_level_fields() -> None:
    widget = SimpleNamespace(
        _field_order=[
            "pipeline_state_dir_name",
            "enabled_route_families",
            "fallback_for_other_scopes",
            "healthcheck_timeout_seconds",
            "editable",
        ],
        _field_specs={
            "enabled_route_families": {"kind": "string_list", "widget": _Textbox("Images\nFiles\nTables\n")},
            "healthcheck_timeout_seconds": {"kind": "int", "widget": _Entry("30")},
            "pipeline_state_dir_name": {"kind": "string", "widget": _Entry("pipeline")},
            "fallback_for_other_scopes": {"kind": "json_object", "widget": _Textbox('{"optimizer": {".txt": ["renderer-html"]}}')},
            "editable": {"kind": "bool", "widget": object(), "variable": _Var(True)},
        }
    )

    payload = read_nested_policy_value(widget)

    assert list(payload) == [
        "pipeline_state_dir_name",
        "enabled_route_families",
        "fallback_for_other_scopes",
        "healthcheck_timeout_seconds",
        "editable",
    ]
    assert payload == {
        "pipeline_state_dir_name": "pipeline",
        "enabled_route_families": ["Images", "Files", "Tables"],
        "fallback_for_other_scopes": {"optimizer": {".txt": ["renderer-html"]}},
        "healthcheck_timeout_seconds": 30,
        "editable": True,
    }


def test_read_nested_policy_value_reports_field_specific_json_errors() -> None:
    widget = SimpleNamespace(
        _field_specs={
            "suffix_groups": {"kind": "json_object", "widget": _Textbox("{invalid json")},
        }
    )

    try:
        read_nested_policy_value(widget)
    except ValueError as exc:
        assert "suffix_groups" in str(exc)
    else:
        raise AssertionError("Expected field-specific JSON error")
