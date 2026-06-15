from __future__ import annotations

from pathlib import Path

from surfaces_support import bundle_workflow, entry


def test_load_bundle_renders_editable_env_files_as_forms(tmp_path: Path, monkeypatch) -> None:
    descriptors = (
        {
            "surface_id": "interpreter.runtime_policy_env",
            "label": "Runtime Policy",
            "kind": "policy",
            "storage_kind": "env_file",
            "editable": True,
            "source_path": "config/runtime_policy.env",
            "section": "Settings",
        },
    )

    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        if payload["action"] == "describe_surfaces":
            return {"status": "ok", "surfaces": descriptors, "module_summary": ""}
        return {"status": "ok", "value": {"LOG_LEVEL": "INFO", "OPENAI_API_BASE_URL": "https://api.openai.com/v1", "DEBUG_BUNDLE_DIR": ""}}

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)
    bundle = bundle_workflow.load_bundle(entry(), state_root=tmp_path)

    assert bundle.surfaces[0].editor_kind == "form"


def test_load_bundle_prefers_explicit_editor_kind_from_descriptor(tmp_path: Path, monkeypatch) -> None:
    descriptors = (
        {
            "surface_id": "normalizer.taxonomy_release_draft",
            "label": "Taxonomy / Projection Release",
            "kind": "taxonomy_release_draft",
            "editable": True,
            "editor_kind": "taxonomy_release_draft",
            "source_path": "Artifact Tree / Semantic Release/releases/*/release.json",
            "section": "Prompts/Assets",
        },
    )

    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        if payload["action"] == "describe_surfaces":
            return {"status": "ok", "surfaces": descriptors, "module_summary": ""}
        return {"status": "ok", "value": {"release": {}, "verification": {"status": "not_loaded"}}}

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)
    bundle = bundle_workflow.load_bundle(entry(), state_root=tmp_path)

    assert bundle.surfaces[0].editor_kind == "taxonomy_release_draft"


def test_load_bundle_keeps_explicit_nested_policy_editor(tmp_path: Path, monkeypatch) -> None:
    descriptors = (
        {
            "surface_id": "orchestrator.execution_policy",
            "label": "Execution Policy",
            "kind": "policy",
            "editable": True,
            "editor_kind": "nested_policy",
            "field_groups": [{"label": "Timeouts", "fields": ["healthcheck_timeout_seconds", "operation_timeouts_seconds"]}],
            "source_path": "config/execution_policy.json",
            "section": "Settings",
        },
    )

    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        if payload["action"] == "describe_surfaces":
            return {"status": "ok", "surfaces": descriptors, "module_summary": ""}
        return {"status": "ok", "value": {"healthcheck_timeout_seconds": 30, "operation_timeouts_seconds": {"extract_document": 1800}}}

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)
    bundle = bundle_workflow.load_bundle(entry(), state_root=tmp_path)

    assert bundle.surfaces[0].editor_kind == "nested_policy"
