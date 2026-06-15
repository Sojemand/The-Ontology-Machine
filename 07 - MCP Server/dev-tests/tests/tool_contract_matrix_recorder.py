from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server import tool_handlers_pipeline_run
from tests.tool_contract_matrix_helpers import _write_empty_sqlite, _write_json
from tests.tool_contract_matrix_types import Call
from tests.tool_contract_matrix_recorder_support import _FakeProcess, _active_release_payload

class OwnerCallRecorder:
    def __init__(self, paths: dict[str, str]) -> None:
        self.paths = paths
        self.product_calls: list[Call] = []
        self.edit_calls: list[Call] = []
        self.admin_calls: list[Call] = []
        self._working_release_locale = "de"
        self._working_release_projection_ids: list[str] = []
        self._active_release_by_db: dict[str, dict[str, Any]] = {}

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        tool_handlers._PIPELINE_RUN_PROCESSES.clear()
        monkeypatch.setattr(tool_handlers, "_invoke_product", self.invoke_product)
        monkeypatch.setattr(tool_handlers, "_invoke_edit", self.invoke_edit)
        monkeypatch.setattr(tool_handlers, "_invoke_admin", self.invoke_admin)
        monkeypatch.setattr(
            tool_handlers_pipeline_run,
            "subprocess",
            type("_PipelineRunSubprocess", (), {"Popen": staticmethod(lambda *_args, **_kwargs: _FakeProcess())}),
        )
        if "orchestrator_ui_state_path" in self.paths:
            monkeypatch.setattr(
                tool_handlers,
                "_orchestrator_ui_state_path",
                lambda: Path(self.paths["orchestrator_ui_state_path"]),
            )
        if "pipeline_runs_dir" in self.paths:
            monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: Path(self.paths["pipeline_runs_dir"]))

    def invoke_product(self, module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        self.product_calls.append((module_key, dict(payload)))
        action = str(payload.get("action") or "")
        if action == "read_active_semantic_release":
            release = _active_release_payload()
            return {
                "status": "ok",
                "detail": {
                    "status": {"runtime_truth_source": "db_active_snapshot"},
                    "release": release,
                    "release_id": release["release_id"],
                    "release_version": release["release_version"],
                    "fingerprint": release["fingerprint"],
                    "release_path": "db://semantic_snapshots/test",
                    "active_snapshot": {"snapshot_id": "snapshot-test"},
                },
            }
        if action == "export_default_blueprint_release":
            output_path = str(payload.get("output_path") or self.paths["exported_release"])
            _write_json(Path(output_path), {"release_id": "default", "locale": payload.get("target_locale") or "en"})
            return {"status": "OK", "output_path": output_path}
        if action == "create_empty_corpus_db":
            _write_empty_sqlite(Path(str(payload["corpus_db_path"])))
        if action == "reset_active_corpus_db":
            db_path = Path(str(payload["corpus_db_path"]))
            db_path.unlink(missing_ok=True)
            db_path.with_name(f"{db_path.name}-wal").unlink(missing_ok=True)
            db_path.with_name(f"{db_path.name}-shm").unlink(missing_ok=True)
            _write_empty_sqlite(db_path)
        if action == "activate_semantic_release":
            db_path = payload.get("corpus_db_path")
            if db_path:
                _write_empty_sqlite(Path(str(db_path)))
                release_payload: dict[str, Any] = {}
                release_path = payload.get("release_path")
                if release_path and Path(str(release_path)).exists():
                    release_payload = json.loads(Path(str(release_path)).read_text(encoding="utf-8"))
                self._active_release_by_db[str(db_path)] = {
                    "runtime_locale": release_payload.get("runtime_locale")
                    or release_payload.get("locale")
                    or self._working_release_locale,
                    "projection_ids": release_payload.get("projection_ids") or self._working_release_projection_ids,
                }
        if action == "read_active_semantic_release":
            release = self._active_release_by_db.get(
                str(payload.get("corpus_db_path") or ""),
                {"runtime_locale": self._working_release_locale, "projection_ids": self._working_release_projection_ids},
            )
            return {
                "status": "ok",
                "detail": {
                    "status": {"active_runtime_locale": release["runtime_locale"]},
                    "release": release,
                },
            }
        return {"status": "ok", "module": module_key, "action": action}

    def invoke_edit(self, module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        self.edit_calls.append((module_key, dict(payload)))
        action = str(payload.get("action") or "")
        if action == "create_release_package":
            self._working_release_locale = str(payload.get("default_runtime_locale") or self._working_release_locale)
            projection_ids = payload.get("projection_ids")
            self._working_release_projection_ids = list(projection_ids) if isinstance(projection_ids, list) else []
            return {
                "status": "ok",
                "runtime_locale": self._working_release_locale,
                "projection_ids": self._working_release_projection_ids,
            }
        if action == "export_semantic_release":
            output_path = str(payload.get("output_path") or self.paths["exported_release"])
            locale = str(payload.get("target_locale") or self._working_release_locale)
            _write_json(
                Path(output_path),
                {
                    "release_id": "working",
                    "locale": locale,
                    "runtime_locale": locale,
                    "projection_ids": self._working_release_projection_ids,
                },
            )
            return {
                "status": "ok",
                "output_path": output_path,
                "runtime_locale": locale,
                "projection_ids": self._working_release_projection_ids,
            }
        if action == "read_release_package":
            return {
                "status": "ok",
                "value": {
                    "release_id": "semantic_release.test",
                    "release_version": "1.0.0",
                    "available_locales": ["de", "en"],
                    "default_authoring_locale": "de",
                    "default_runtime_locale": "de",
                    "projection_ids": ["finance.default.v1", "fantasy.story.default.v1"],
                },
            }
        if action == "read_translation_glossary_locale":
            locale = str(payload.get("locale") or "de")
            return {
                "status": "ok",
                "allowed_values": ["de", "en"],
                "value": {
                    "active_locale": locale,
                    "entries": [
                        {
                            "english_term": "invoice",
                            "canonical": "Rechnung" if locale == "de" else "Invoice",
                            "aliases": ["Rechnungsbeleg"] if locale == "de" else [],
                        }
                    ],
                },
            }
        if action == "list_projections":
            return {
                "status": "ok",
                "value": {
                    "projections": [
                        {"projection_id": "finance.default.v1", "label": "Finance"},
                        {"projection_id": "fantasy.story.default.v1", "label": "Fantasy Story"},
                    ]
                },
            }
        return {"status": "ok", "module": module_key, "action": action}

    def invoke_admin(self, module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.admin_calls.append((module_key, dict(payload)))
        return {"status": "ok", "module": module_key, "action": payload.get("action")}
