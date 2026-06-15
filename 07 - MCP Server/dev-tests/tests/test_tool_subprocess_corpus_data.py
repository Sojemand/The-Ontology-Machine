from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.contract_client import ModuleSpec
from mcp_server.tools import call_tool
from tests.tool_subprocess_fixtures import *
from tests.tool_subprocess_helpers import _export_default_release, _seed_document, _write_new_corpus_confirmation, _write_reset_confirmation

@pytest.mark.integration
def test_l2_initialized_corpus_data_tools_use_real_schema_and_rows(
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
    _seed_document(db_path, "invoice-l2", free_text="alpha invoice electricity amount")

    search = call_tool("search_corpus", {"query": "electricity", "mode": "Fulltext", "limit": 5, "corpus_db_path": db_path})
    stats = call_tool("corpus_stats", {"corpus_db_path": db_path})
    exported = call_tool(
        "export_corpus",
        {"corpus_db_path": db_path, "output_path": integration_paths["export_path"], "fmt": "jsonl"},
    )
    backfill = call_tool("backfill_stale", {"corpus_db_path": db_path, "stale_only": True, "limit": 5})
    embeddings = call_tool(
        "generate_embeddings",
        {"corpus_db_path": db_path, "runtime_model": "text-embedding-3-small"},
    )

    assert search["status"] == "ok"
    assert search["detail"]["results"]
    assert stats["status"] == "ok"
    assert stats["detail"]["total_documents"] == 1
    assert exported["status"] == "ok"
    assert Path(integration_paths["export_path"]).exists()
    assert backfill["status"] == "ok"
    assert embeddings["status"] in {"disabled", "ok"}


@pytest.mark.integration
def test_l2_merge_tools_use_real_initialized_databases(
    isolated_owner_specs: dict[str, ModuleSpec],
    integration_paths: dict[str, str],
) -> None:
    release = _export_default_release(integration_paths["release_path"])
    source_db = integration_paths["source_db"]
    target_db = integration_paths["target_db"]
    call_tool("activate_release_on_existing_db", {"release_path": release, "corpus_db_path": source_db})
    call_tool("activate_release_on_existing_db", {"release_path": release, "corpus_db_path": target_db})
    _seed_document(source_db, "source-doc", free_text="source merge document")
    _seed_document(target_db, "target-doc", free_text="target merge document")

    preflight = call_tool("merge_preflight", {"source_db_path": source_db, "target_db_path": target_db})
    assert preflight["status"] == "ok"
    assert preflight["detail"]["blocked"] is False

    merge_args: dict[str, str] = {"source_db_path": source_db, "target_db_path": target_db}
    pending = preflight["detail"].get("pending_interactions") or []
    for interaction in pending:
        arg_name = str(interaction["artifact_argument_name"])
        path = Path(integration_paths["confirmation_dir"]) / f"{interaction['kind']}.json"
        _write_json(path, dict(interaction["artifact_template"]))
        merge_args[arg_name] = str(path)

    merged = call_tool("merge_corpora", merge_args)
    assert merged["status"] == "ok"
    assert merged["detail"]["imported_document_count"] == 1
