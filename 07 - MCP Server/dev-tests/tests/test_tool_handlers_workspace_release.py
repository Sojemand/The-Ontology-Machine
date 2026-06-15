from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool


def test_verify_workspace_active_release_reads_db_and_checks_selection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_root = tmp_path / "Artifacts Test"
    corpus_root = artifact_root / "Corpus"
    corpus_root.mkdir(parents=True)
    corpus_db = corpus_root / "Fantasie.db"
    sqlite3.connect(corpus_db).close()
    product_calls: list[tuple[str, dict[str, Any]]] = []

    def fake_product(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        product_calls.append((module_key, payload))
        return {
            "status": "ok",
            "detail": {
                "status": {"active_runtime_locale": "en"},
                "release": {
                    "runtime_locale": "en",
                    "projection_ids": ["fantasy.story.default.v1"],
                },
            },
        }

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_product)

    result = call_tool(
        "verify_workspace_active_release",
        {
            "artifact_folder": str(artifact_root),
            "database_name": "Fantasie",
            "language": "en",
            "projection_ids": ["fantasy.story.default.v1"],
        },
    )

    assert result["status"] == "ok"
    assert result["language"] == "en"
    assert result["corpus_db_path"] == str(corpus_db.resolve())
    assert result["verification"]["verified"] is True
    assert result["verification"]["runtime_locale"] == "en"
    assert result["verification"]["projection_ids"] == ["fantasy.story.default.v1"]
    assert product_calls == [
        ("corpus_builder", {"action": "read_active_semantic_release", "corpus_db_path": str(corpus_db.resolve())})
    ]


def test_verify_workspace_active_release_rejects_locale_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_root = tmp_path / "Artifacts Test"
    corpus_root = artifact_root / "Corpus"
    corpus_root.mkdir(parents=True)
    corpus_db = corpus_root / "Fantasie.db"
    sqlite3.connect(corpus_db).close()

    def fake_product(_module_key: str, _payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": {"active_runtime_locale": "de"},
            "release": {
                "runtime_locale": "de",
                "projection_ids": ["fantasy.story.default.v1"],
            },
        }

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_product)

    with pytest.raises(ToolFailure, match="runtime_locale 'de', erwartet war 'en'"):
        call_tool(
            "verify_workspace_active_release",
            {
                "artifact_folder": str(artifact_root),
                "database_name": "Fantasie",
                "language": "en",
                "projection_ids": ["fantasy.story.default.v1"],
            },
        )


def test_write_workspace_release_change_confirmation_writes_only_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_root = tmp_path / "Artifacts Test"
    corpus_root = artifact_root / "Corpus"
    corpus_root.mkdir(parents=True)
    corpus_db = corpus_root / "Fantasie.db"
    release_path = corpus_root / "Fantasie.semantic_release.json"
    product_calls: list[tuple[str, dict[str, Any]]] = []
    edit_calls: list[tuple[str, dict[str, Any]]] = []

    monkeypatch.setattr(tool_handlers, "_invoke_product", lambda module, payload: product_calls.append((module, payload)))
    monkeypatch.setattr(tool_handlers, "_invoke_edit", lambda module, payload, **_kwargs: edit_calls.append((module, payload)))

    result = call_tool(
        "write_workspace_release_change_confirmation",
        {
            "artifact_folder": str(artifact_root),
            "database_name": "Fantasie",
            "activation_decision": "activate_and_backfill",
            "confirm_release_change": True,
            "activation_preflight_result": {
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
            },
        },
    )

    confirmation_path = Path(result["confirmation_artifact_path"])
    confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert confirmation_path == corpus_root.resolve() / "Fantasie.release-change.confirmation.json"
    assert confirmation["decision"] == "activate_and_backfill"
    assert confirmation["confirmed_by_tool"] == "write_workspace_release_change_confirmation"
    assert product_calls == []
    assert edit_calls == []
