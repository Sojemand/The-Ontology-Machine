from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.contract_client import ContractError
from mcp_server.tools import call_tool


def test_release_revision_atomics_block_taxonomy_line_change(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    artifact_root, corpus_db, release_path = _workspace_with_document(tmp_path, "review")
    _write_release(
        release_path,
        master_taxonomy_release_id="sha256:new",
        fingerprint="sha256:candidate",
        projection_ids=["fantasy.story.custom.v2"],
    )

    def fake_product(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        if payload["action"] == "semantic_status":
            return {"active_master_taxonomy_release_id": "sha256:old", "active_release_fingerprint": "sha256:old-release"}
        if payload["action"] == "read_active_semantic_release":
            return {"release": {"master_taxonomy_release_id": "sha256:old", "fingerprint": "sha256:old-release"}}
        if payload["action"] == "activation_preflight":
            raise ContractError("Semantic Release kann nicht aktiviert werden: unterschiedliche master_taxonomy_release_id.")
        return {"status": "ok", "module": module_key}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_product)

    candidate = call_tool("read_revision_candidate_release", {"release_path": str(release_path)})
    context = call_tool("inspect_release_revision_context", {"corpus_db_path": str(corpus_db)})
    result = call_tool(
        "classify_release_revision",
        {
            "database_state": context["database_state"],
            "candidate_release": candidate["candidate_release"],
            "active_release": context["active_release"],
            "activation_preflight_error": "Semantic Release kann nicht aktiviert werden: unterschiedliche master_taxonomy_release_id.",
        },
    )

    plan = result["revision_plan"]
    assert result["status"] == "needs_user_decision"
    assert plan["change_class"] == "master_taxonomy_changed"
    assert plan["backfill_supported"] is False
    assert plan["requires_reset_or_new_db"] is True
    assert "backfill_stale" in plan["blocked_steps"]


def test_write_workspace_release_change_confirmation_writes_confirmation_for_backfill(tmp_path) -> None:
    artifact_root, corpus_db, release_path = _workspace_with_document(tmp_path, "active")

    result = call_tool(
        "write_workspace_release_change_confirmation",
        {
            "artifact_folder": str(artifact_root),
            "database_name": "Fantasie",
            "activation_preflight_result": _same_master_preflight(corpus_db, release_path),
            "confirm_release_change": True,
            "activation_decision": "activate_and_backfill",
        },
    )

    confirmation_path = Path(result["confirmation_artifact_path"])
    confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    assert confirmation["decision"] == "activate_and_backfill"
    assert confirmation["confirmed_by_tool"] == "write_workspace_release_change_confirmation"


def _workspace_with_document(tmp_path, suffix: str) -> tuple[Path, Path, Path]:
    artifact_root = tmp_path / f"Artifacts Test {suffix}"
    corpus_root = artifact_root / "Corpus"
    corpus_root.mkdir(parents=True)
    corpus_db = corpus_root / "Fantasie.db"
    conn = sqlite3.connect(corpus_db)
    conn.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, is_archived INTEGER DEFAULT 0)")
    conn.execute("INSERT INTO documents (id, is_archived) VALUES ('doc-1', 0)")
    conn.commit()
    conn.close()
    return artifact_root, corpus_db, corpus_root / "Fantasie.semantic_release.review.json"


def _write_release(path: Path, *, master_taxonomy_release_id: str, fingerprint: str, projection_ids: list[str]) -> None:
    path.write_text(
        json.dumps(
            {
                "release_id": "fantasy.custom",
                "runtime_locale": "de",
                "master_taxonomy_release_id": master_taxonomy_release_id,
                "fingerprint": fingerprint,
                "projection_ids": projection_ids,
            }
        ),
        encoding="utf-8",
    )


def _same_master_preflight(corpus_db: Path, release_path: Path) -> dict[str, Any]:
    return {
        "requires_confirmation": True,
        "db_changes": {"projection_drift_documents": 0},
        "confirmation_artifact_template": {
            "artifact_version": "semantic_activation_confirmation_v1",
            "corpus_db_path": str(corpus_db.resolve()),
            "release_path": str(release_path),
            "expected_current_snapshot_id": "old",
            "expected_new_snapshot_id": "new",
            "expected_release_fingerprint": "sha256:new",
            "expected_master_taxonomy_release_id": "sha256:same",
            "expected_runtime_locale": "de",
            "decision": "activate_only",
        },
    }
