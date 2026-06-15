from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from orchestrator.models import UiState
from orchestrator.pipeline import policy as pipeline_policy
from orchestrator.state import load_pipeline_state


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def make_regression_ui_state(tmp_path: Path, case_dir: Path) -> UiState:
    input_dir = tmp_path / "input"
    artifact_dir = tmp_path / "artifacts"
    corpus_dir = artifact_dir / "Corpus"
    for path in (input_dir, artifact_dir, corpus_dir):
        path.mkdir(parents=True, exist_ok=True)
    shutil.copytree(case_dir / "input", input_dir, dirs_exist_ok=True)
    return UiState(input_folder=str(input_dir), artifact_folder=str(artifact_dir), corpus_output_folder=str(corpus_dir))


def load_regression_record(ui_state: UiState):
    state_path = Path(ui_state.input_folder).parent / "orchestrator" / "state" / "pipeline" / "pipeline_state.json"
    return next(iter(load_pipeline_state(state_path).documents.values()))


def assert_regression_case(case: dict, ui_state: UiState, summary, record) -> None:
    expected = case["expected"]
    for key, value in expected["summary"].items():
        assert getattr(summary, key) == value
    for key, value in expected["record"].items():
        assert getattr(record, key) == value
    for dotted, suffix in expected.get("suffixes", {}).items():
        actual = normalize_path_text(dotted_value(record, dotted))
        assert actual.endswith(render_template(suffix, record))
    artifact_root = Path(ui_state.artifact_folder)
    for rel_path in expected.get("present", []):
        assert (artifact_root / render_template(rel_path, record)).exists()
    for rel_path in expected.get("absent", []):
        assert not (artifact_root / render_template(rel_path, record)).exists()
    assert (Path(ui_state.corpus_output_folder) / "corpus.db").exists() is bool(expected.get("corpus_db", False))
    if expected.get("manifest"):
        manifest = expected["manifest"]
        payload = read_json(artifact_root / render_template(manifest["path"], record))
        for key, value in manifest["fields"].items():
            assert payload[key] == (render_template(value, record) if isinstance(value, str) else value)


def copy_fixture(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def default_report_name(structured_path: Path) -> str:
    payload = read_json(structured_path)
    processing = payload.get("processing", {}) if isinstance(payload, dict) else {}
    profile = str(processing.get("interpreter_profile", "vision")).strip() or "vision"
    suffix = ".files_validation_report.json" if profile == "file" else ".vision_validation_report.json"
    if structured_path.name.endswith(".structured.json"):
        return structured_path.name[: -len(".structured.json")] + suffix
    return f"{structured_path.stem}{suffix}"


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def render_template(text: str, record) -> str:
    bundle_name = f"{pipeline_policy.bundle_slug(record)}.{pipeline_policy.hash8(record.content_hash)}"
    return text.format(hash8=pipeline_policy.hash8(record.content_hash), bundle_name=bundle_name)


def dotted_value(record, dotted: str):
    value = record
    for part in dotted.split("."):
        value = getattr(value, part)
    return value


def normalize_path_text(value: str) -> str:
    return value.replace("\\", "/")
