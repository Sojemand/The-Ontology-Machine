from __future__ import annotations

import importlib

from form_fields_support import _entry

bundle_workflow = importlib.import_module("edit_suite.surfaces.load_bundle")


def test_load_bundle_uses_field_groups_to_render_policy_as_form(tmp_path, monkeypatch) -> None:
    descriptors = (
        {
            "surface_id": "validator.report_preview_policy",
            "label": "Report Preview Policy",
            "kind": "policy",
            "storage_kind": "json_file",
            "editable": True,
            "source_path": "config/config.json",
            "section": "Settings",
            "field_groups": [{"label": "Policy", "fields": ["flag_needs_review", "max_issues_per_check"]}],
        },
    )

    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        if payload["action"] == "describe_surfaces":
            return {"status": "ok", "surfaces": descriptors, "module_summary": ""}
        return {"status": "ok", "value": {"flag_needs_review": True, "max_issues_per_check": 20}}

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)

    bundle = bundle_workflow.load_bundle(_entry(), state_root=tmp_path)

    assert bundle.surfaces[0].editor_kind == "form"
