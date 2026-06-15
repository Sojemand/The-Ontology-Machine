from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.contract_client import ModuleSpec
from mcp_server.tools import call_tool
from tests.tool_subprocess_fixtures import *
from tests.tool_subprocess_helpers import _export_default_release, _seed_document, _write_new_corpus_confirmation, _write_reset_confirmation

@pytest.mark.integration
def test_l2_corpus_context_reset_and_release_activation_use_real_subprocesses(
    isolated_owner_specs: dict[str, ModuleSpec],
    integration_paths: dict[str, str],
) -> None:
    release = _export_default_release(integration_paths["release_path"])

    created = call_tool(
        "create_empty_corpus_db",
        {
            "corpus_db_path": integration_paths["fresh_db"],
            "corpus_output_folder": integration_paths["corpus_root"],
        },
    )
    assert created["status"] == "ok", created
    assert Path(integration_paths["fresh_db"]).exists()

    active_db = integration_paths["active_db"]
    preflight = call_tool("activation_preflight", {"release_path": release, "corpus_db_path": active_db})
    activated = call_tool(
        "activate_release_on_existing_db",
        {"release_path": release, "corpus_db_path": active_db},
    )
    context = call_tool(
        "activate_corpus_context",
        {"corpus_db_path": active_db, "corpus_output_folder": integration_paths["corpus_root"]},
    )
    status = call_tool("inspect_active_corpus", {"corpus_db_path": active_db})
    active_release = call_tool("read_active_semantic_release", {"corpus_db_path": active_db})
    audit = call_tool("semantic_audit", {"corpus_db_path": active_db})
    loaded = call_tool("load_semantic_release", {"release_path": release, "corpus_db_path": active_db})
    assert activated["status"] in {"ok", "applied"}
    assert context["status"] == "ok"
    assert status["status"] == "ok"
    assert active_release["status"] == "ok"
    assert audit["status"] == "ok"
    assert preflight["status"] == "ok"
    assert loaded["status"] == "ok"

    confirmation = _write_reset_confirmation(integration_paths, active_db)
    reset = call_tool(
        "reset_active_corpus_db",
        {"corpus_db_path": active_db, "confirmation_artifact_path": str(confirmation)},
    )
    assert reset["status"] == "ok"
    assert Path(active_db).exists()


@pytest.mark.integration
def test_l2_corpus_creation_flows_use_real_release_bundles(
    isolated_owner_specs: dict[str, ModuleSpec],
    integration_paths: dict[str, str],
) -> None:
    exported = call_tool(
        "export_default_blueprint_release",
        {
            "blueprint_ref": "default",
            "target_locale": "en",
            "output_path": integration_paths["release_path"],
        },
    )
    assert exported["status"] == "OK"
    created = call_tool(
        "create_empty_corpus_db",
        {
            "corpus_db_path": integration_paths["blueprint_db"],
            "corpus_output_folder": integration_paths["corpus_root"],
        },
    )
    preflight = call_tool(
        "activation_preflight",
        {"release_path": integration_paths["release_path"], "corpus_db_path": integration_paths["blueprint_db"]},
    )
    activated = call_tool(
        "activate_release_on_existing_db",
        {"release_path": integration_paths["release_path"], "corpus_db_path": integration_paths["blueprint_db"]},
    )
    context = call_tool(
        "activate_corpus_context",
        {"corpus_db_path": integration_paths["blueprint_db"], "corpus_output_folder": integration_paths["corpus_root"]},
    )
    assert created["status"] == "ok"
    assert preflight["status"] == "ok"
    assert activated["status"] in {"ok", "applied"}
    assert context["status"] == "ok"
    assert Path(integration_paths["blueprint_db"]).exists()
    assert Path(integration_paths["release_path"]).exists()

    workspace = call_tool(
        "prepare_pipeline_workspace_root",
        {"artifact_folder": integration_paths["workspace_artifact_root"]},
    )
    workspace_db = Path(integration_paths["workspace_artifact_root"]) / "Corpus" / "Fantasy_Story.db"
    workspace_created = call_tool(
        "create_empty_corpus_db",
        {"corpus_db_path": str(workspace_db), "corpus_output_folder": workspace["corpus_output_folder"]},
    )
    workspace_context = call_tool(
        "activate_corpus_context",
        {
            "corpus_db_path": str(workspace_db),
            "corpus_output_folder": workspace["corpus_output_folder"],
            "artifact_folder": workspace["artifact_folder"],
            "input_folder": workspace["input_folder"],
        },
    )
    assert workspace["status"] == "ok"
    assert workspace["input_folder"] == str((Path(integration_paths["workspace_artifact_root"]) / "Input").resolve())
    assert workspace_created["status"] == "ok"
    assert workspace_context["status"] == "ok"
    assert workspace_db.exists()
    assert (Path(integration_paths["workspace_artifact_root"]) / "Input").is_dir()
    assert (Path(integration_paths["workspace_artifact_root"]) / "Documents" / "structured").is_dir()
