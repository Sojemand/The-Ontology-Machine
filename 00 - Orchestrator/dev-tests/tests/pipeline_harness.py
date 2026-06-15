from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from orchestrator.models import UiState
from orchestrator.pipeline import OrchestratorEngine
import orchestrator.pipeline.storage_repository as storage_repository
from orchestrator.state import load_pipeline_state


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def make_ui_state(tmp_path: Path, mode: str = "batch") -> UiState:
    input_dir = tmp_path / "input"
    artifact_dir = tmp_path / "artifacts"
    corpus_dir = artifact_dir / "Corpus"
    for path in (input_dir, artifact_dir, corpus_dir):
        path.mkdir(parents=True, exist_ok=True)
    return UiState(
        input_folder=str(input_dir),
        artifact_folder=str(artifact_dir),
        corpus_output_folder=str(corpus_dir),
        mode=mode,
    )


def create_source(ui_state: UiState, relative_path: str = "doc.pdf", *, content: str = "doc") -> Path:
    path = Path(ui_state.input_folder) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def artifact_root(ui_state: UiState) -> Path:
    return Path(ui_state.artifact_folder)


def route_root(ui_state: UiState, route_family: str = "Documents") -> Path:
    return storage_repository.route_artifact_root(ui_state, route_family)


def error_root(ui_state: UiState) -> Path:
    return storage_repository.error_root(ui_state)


def error_case_root(ui_state: UiState, module_name: str, route_family: str = "Documents") -> Path:
    return storage_repository.error_case_route_root(ui_state, module_name, route_family)


def legacy_error_root(ui_state: UiState) -> Path:
    return artifact_root(ui_state) / "errors"


def route_logs_root(ui_state: UiState, route_family: str = "Documents") -> Path:
    return storage_repository.route_logs_root(ui_state, route_family)


def make_engine(tmp_path: Path, scenarios: dict[str, dict[str, object]]) -> OrchestratorEngine:
    from tests.pipeline_fake_modules import FakeModules

    orchestrator_root = tmp_path / "orchestrator"
    orchestrator_root.mkdir(parents=True, exist_ok=True)
    return OrchestratorEngine(orchestrator_root=orchestrator_root, modules=FakeModules(scenarios))


def orchestrator_logs_root(tmp_path: Path) -> Path:
    return tmp_path / "orchestrator" / "state" / "pipeline"


def pipeline_state_path(tmp_path: Path) -> Path:
    return orchestrator_logs_root(tmp_path) / "pipeline_state.json"


def runtime_files(tmp_path: Path) -> list[Path]:
    runtime_root = orchestrator_logs_root(tmp_path) / "runs"
    return sorted(
        path
        for path in runtime_root.rglob("*")
        if path.is_file()
        and path.name not in {"run.log", "runtime_semantic_assets.json", "optimizer_runtime_semantic_assets.json"}
    )


def run_log_files(tmp_path: Path) -> list[Path]:
    runtime_root = orchestrator_logs_root(tmp_path) / "runs"
    return sorted(path for path in runtime_root.rglob("run.log") if path.is_file())


def lock_path(tmp_path: Path) -> Path:
    return tmp_path / "orchestrator" / "state" / "orchestrator.lock"


def load_single_record(tmp_path: Path):
    state = load_pipeline_state(pipeline_state_path(tmp_path))
    return next(iter(state.documents.values()))


def saved_record(content_hash: str, **overrides: Any) -> dict[str, Any]:
    record = {
        "content_hash": content_hash,
        "file_name": "doc.pdf",
        "relative_path": "doc.pdf",
        "original_source_path": "",
        "source_path": "",
        "current_location": "error_bundle",
        "status": "error",
        "final_disposition": "",
        "attempts": 1,
        "failed_attempts": 1,
        "last_stage": "Interpreter",
        "last_error": "boom",
        "review_reason": "",
        "validator_needs_review": False,
        "validator_review_reason": "",
        "artifacts": {},
        "created_at": "now",
        "updated_at": "now",
        "last_processed_at": "now",
    }
    record.update(overrides)
    record["artifacts"] = dict(record.get("artifacts", {}))
    return record


def write_saved_state(tmp_path: Path, *records: dict[str, Any]) -> None:
    path = pipeline_state_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": "now",
        "documents": {record["content_hash"]: record for record in records},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
