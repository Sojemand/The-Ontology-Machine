from __future__ import annotations

import json
from pathlib import Path

from normalizer_vision.models import load_config
from normalizer_vision.normalizer import DocumentNormalizer

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "regression"


class FixtureProvider:
    def __init__(self, payload: dict):
        self.payload = payload

    def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
        return json.dumps(self.payload)

    def is_available(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "openai"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _prepare_case(tmp_project_root: Path, monkeypatch, case_name: str, normalizer_runtime_settings):
    monkeypatch.setattr("normalizer_vision.normalizer.document.utc_now_iso", lambda: "2026-03-27T00:00:00Z")
    structured_path = tmp_project_root / f"{case_name}.structured.json"
    structured_path.write_text((FIXTURE_ROOT / f"{case_name}.structured.json").read_text(encoding="utf-8"), encoding="utf-8")
    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=FixtureProvider(_load_json(f"{case_name}.model_output.json")),
    )
    return structured_path, normalizer


def _normalized_output_path(project_root: Path, structured_path: Path) -> Path:
    return project_root / "output" / structured_path.name.replace(".structured.json", ".structured.normalized.json")


def test_regression_case_a_prompt_preview_matches_snapshot(tmp_project_root, monkeypatch, normalizer_runtime_settings):
    structured_path, normalizer = _prepare_case(tmp_project_root, monkeypatch, "case_a", normalizer_runtime_settings)
    system_prompt, user_prompt = normalizer.build_prompt_preview(structured_path)
    expected = _load_json("case_a.prompt_preview.json")

    assert system_prompt == expected["system_prompt"]
    assert user_prompt == expected["user_prompt"]


def test_regression_case_a_normalized_output_matches_snapshot(tmp_project_root, monkeypatch, normalizer_runtime_settings):
    structured_path, normalizer = _prepare_case(tmp_project_root, monkeypatch, "case_a", normalizer_runtime_settings)
    result = normalizer.normalize(structured_path, _normalized_output_path(tmp_project_root, structured_path))

    assert json.loads(Path(result.output_path).read_text(encoding="utf-8")) == _load_json("case_a.expected.normalized.json")


def test_regression_case_b_normalized_output_matches_snapshot(tmp_project_root, monkeypatch, normalizer_runtime_settings):
    structured_path, normalizer = _prepare_case(tmp_project_root, monkeypatch, "case_b", normalizer_runtime_settings)
    result = normalizer.normalize(structured_path, _normalized_output_path(tmp_project_root, structured_path))

    assert json.loads(Path(result.output_path).read_text(encoding="utf-8")) == _load_json("case_b.expected.normalized.json")
