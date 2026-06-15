from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.contract_client import ModuleSpec
from mcp_server.tools import call_tool
from tests.tool_subprocess_fixtures import *
from tests.tool_subprocess_helpers import _export_default_release, _seed_document, _write_new_corpus_confirmation, _write_reset_confirmation

@pytest.mark.integration
def test_l2_artifact_rebuild_tools_use_real_artifact_files(
    isolated_owner_specs: dict[str, ModuleSpec],
    integration_paths: dict[str, str],
) -> None:
    release = _export_default_release(integration_paths["release_path"])
    db_path = integration_paths["active_db"]
    call_tool("activate_release_on_existing_db", {"release_path": release, "corpus_db_path": db_path})
    call_tool(
        "activate_corpus_context",
        {"corpus_db_path": db_path, "corpus_output_folder": integration_paths["corpus_root"]},
    )
    args = {
        "pipeline_root": integration_paths["artifact_root"],
        "corpus_db_path": db_path,
    }

    preview = call_tool("preview_rebuild_from_artifacts", {"pipeline_root": integration_paths["artifact_root"], "corpus_db_path": db_path})
    rebuild = call_tool("rebuild_corpus_from_artifacts", {**args, "replace_existing": False})
    assert preview["status"] == "ok"
    assert preview["detail"]["bundle_count"] == 1
    assert rebuild["status"] == "ok"
    assert rebuild["detail"]["result"]["loaded"] == 1, rebuild

    new_db = integration_paths["fresh_db"]
    created = call_tool(
        "create_empty_corpus_db",
        {"corpus_db_path": new_db, "corpus_output_folder": integration_paths["corpus_root"]},
    )
    preflight_new = call_tool("activation_preflight", {"release_path": release, "corpus_db_path": new_db})
    activated_new = call_tool("activate_release_on_existing_db", {"release_path": release, "corpus_db_path": new_db})
    context_new = call_tool(
        "activate_corpus_context",
        {"corpus_db_path": new_db, "corpus_output_folder": integration_paths["corpus_root"]},
    )
    rebuilt_new = call_tool(
        "rebuild_corpus_from_artifacts",
        {
            "pipeline_root": integration_paths["artifact_root"],
            "corpus_db_path": new_db,
            "replace_existing": False,
        },
    )
    assert created["status"] == "ok", created
    assert preflight_new["status"] == "ok"
    assert activated_new["status"] in {"ok", "applied"}
    assert context_new["status"] == "ok"
    assert rebuilt_new["status"] == "ok", rebuilt_new
    assert rebuilt_new["detail"]["result"]["loaded"] == 1
