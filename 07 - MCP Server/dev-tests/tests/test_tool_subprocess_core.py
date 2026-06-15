from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.contract_client import ModuleSpec
from mcp_server.tool_catalog import tool_definitions
from mcp_server.semantic_control_kernel_visibility import PERMANENT_AGENT_TOOL_NAMES
from mcp_server.tools import call_tool
from tests.tool_subprocess_fixtures import *
from tests.tool_subprocess_helpers import _export_default_release, _seed_document, _write_new_corpus_confirmation, _write_reset_confirmation

@pytest.mark.integration
def test_l2_classifies_every_visible_tool() -> None:
    catalog_names = {tool["name"] for tool in tool_definitions()} - set(PERMANENT_AGENT_TOOL_NAMES)

    assert OFFLINE_SUBPROCESS_TOOLS | GATED_SUBPROCESS_TOOLS == catalog_names
    assert OFFLINE_SUBPROCESS_TOOLS & GATED_SUBPROCESS_TOOLS == frozenset()


@pytest.mark.integration
def test_l2_support_monitor_tools_are_local_and_user_approved(tmp_path: Path) -> None:
    assessed = call_tool(
        "assess_support_incident",
        {
            "classification": "unexpected_exception",
            "confidence": "high",
            "module_key": "normalizer",
            "tool_action": "compile_release_package",
            "severity": "error",
            "status": "exception",
            "message": "Compile failed with token sk-integrationsecret123456",
            "metadata": {"api_key": "secret"},
        },
    )
    assessment_id = assessed["assessment"]["assessment_id"]
    incident_id = assessed["assessment"]["incident_id"]

    incidents = call_tool("list_support_incidents", {})
    preview = call_tool("preview_support_bug_report", {"assessment_id": assessment_id, "user_note": "integration preview"})
    report_path = tmp_path / "support-report.json"
    built = call_tool("build_support_bug_report", {"assessment_id": assessment_id, "output_path": str(report_path)})
    submitted = call_tool("queue_support_bug_report", {"assessment_id": assessment_id, "report_path": built["report_path"], "user_confirmed": True})
    dismissed = call_tool("dismiss_support_incident", {"incident_id": incident_id, "reason": "reported"})

    assert assessed["status"] == "ok"
    assert assessed["reportable"] is True
    assert incidents["incident_count"] == 1
    assert preview["report"]["incident"]["incident_id"] == incident_id
    assert Path(built["report_path"]).exists()
    assert submitted["status"] == "queued"
    assert Path(submitted["queued_path"]).exists()
    assert dismissed["dismissed"] is True


@pytest.mark.integration
def test_l2_introspection_and_edit_surfaces_use_real_subprocesses(
    isolated_owner_specs: dict[str, ModuleSpec],
) -> None:
    pipeline = call_tool("inspect_pipeline_contract_governance", {})
    assert pipeline["status"] == "ok"
    assert pipeline["modules"]["normalizer"]["runtime_python"] == str(isolated_owner_specs["normalizer"].python_executable)

    described = call_tool("describe_owner_surfaces", {"module": "orchestrator"})
    assert described["status"] == "ok"
    surface_id = described["surfaces"][0]["surface_id"]

    bundle = call_tool("read_owner_bundle", {"module": "normalizer"})
    assert bundle["status"] == "ok"
    assert bundle["surfaces"]

    current = call_tool("read_owner_surface", {"module": "orchestrator", "surface_id": surface_id})
    assert current["status"] == "ok"
    validated = call_tool(
        "validate_owner_surface",
        {"module": "orchestrator", "surface_id": surface_id, "value": current["value"]},
    )
    written = call_tool(
        "write_owner_surface",
        {"module": "orchestrator", "surface_id": surface_id, "value": current["value"]},
    )
    assert validated["status"] == "ok"
    assert written["status"] == "ok"


@pytest.mark.integration
def test_l2_normalizer_release_tools_use_real_subprocesses(
    isolated_owner_specs: dict[str, ModuleSpec],
    integration_paths: dict[str, str],
) -> None:
    blueprints = call_tool("list_default_blueprints", {})
    assert blueprints["status"] == "ok"
    assert any(item["blueprint_ref"] == "default" for item in blueprints["blueprints"])

    derived = call_tool(
        "derive_working_release_from_blueprint",
        {"artifact_folder": integration_paths["workspace_artifact_root"], "blueprint_ref": "default"},
    )
    assert derived["status"] == "ok"

    exported = call_tool(
        "export_default_blueprint_release",
        {
            "blueprint_ref": "default",
            "target_locale": "en",
            "output_path": integration_paths["release_path"],
        },
    )
    assert exported["status"] == "OK"
    assert Path(exported["output_path"]).exists()

    validated = call_tool(
        "validate_working_release",
        {"artifact_folder": integration_paths["workspace_artifact_root"], "target_locale": "en"},
    )
    compiled = call_tool(
        "compile_working_release",
        {"artifact_folder": integration_paths["workspace_artifact_root"], "target_locale": "en"},
    )
    assert validated["status"] == "ok"
    assert compiled["status"] == "ok"


@pytest.mark.integration
def test_atomic_translation_glossary_tools_use_real_normalizer_state(
    isolated_owner_specs: dict[str, ModuleSpec],
) -> None:
    listed = call_tool("read_translation_glossary", {"locale": "en"})
    assert listed["status"] == "ok"
    assert listed["locale"] == "en"

    upserted = call_tool(
        "upsert_translation_glossary_entry",
        {
            "locale": "en",
            "english_term": "story outline",
            "canonical": "Story-Outline",
            "aliases": ["Kapitelplan"],
        },
    )
    assert upserted["entry_status"] in {"created", "updated"}
    assert any(item["english_term"] == "story outline" for item in upserted["entries"])

    removed = call_tool(
        "remove_translation_glossary_entry",
        {"locale": "en", "english_term": "story outline"},
    )
    assert removed["entry_status"] == "removed"
    assert all(item["english_term"] != "story outline" for item in removed["entries"])


@pytest.mark.integration
def test_l2_admin_tools_use_isolated_real_state_and_audit(
    isolated_owner_specs: dict[str, ModuleSpec],
) -> None:
    inspected = call_tool("inspect_runtime", {})
    assert inspected["status"] == "ok"

    settings = dict(inspected["runtime_settings"])
    settings["normalizer"] = dict(settings["normalizer"])
    settings["normalizer"]["max_output_tokens"] = 1234
    written = call_tool("write_runtime_settings", {"settings": settings})
    assert written["status"] == "ok"
    assert written["runtime_settings"]["normalizer"]["max_output_tokens"] == 1234

    reset = call_tool("reset_runtime_settings", {})
    assert reset["status"] == "ok"

    set_secret = call_tool(
        "set_runtime_api_key",
        {"target": "llm_shared", "secret_value": "l2-secret-value"},
    )
    revealed = call_tool(
        "reveal_secret",
        {
            "target": "llm_shared",
            "purpose": "l2 integration test",
            "unlock_phrase": "REVEAL_SECRET:llm_shared",
        },
    )
    deleted = call_tool("delete_runtime_api_key", {"target": "llm_shared"})
    assert set_secret["status"] == "ok"
    assert revealed["secret_value"] == "l2-secret-value"
    assert deleted["status"] == "ok"

    audit_path = isolated_owner_specs["orchestrator"].root / "state" / "admin_audit.jsonl"
    audit = audit_path.read_text(encoding="utf-8")
    assert "manage_credentials" in audit
    assert "reveal_secret" in audit
    assert "l2-secret-value" not in audit
