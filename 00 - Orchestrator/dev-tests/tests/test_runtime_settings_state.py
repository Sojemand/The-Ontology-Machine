from __future__ import annotations

import json

import pytest

import orchestrator.state as state_module
from orchestrator.state import load_runtime_settings


def test_load_runtime_settings_defaults_when_file_is_missing(tmp_path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    loaded = load_runtime_settings(state_dir)

    assert loaded.schema_version == 1
    assert loaded.interpreter.model == "gpt-5.4"
    assert loaded.normalizer.max_output_tokens == 15000
    assert loaded.corpus_builder_embeddings.model == "text-embedding-3-small"
    assert loaded.optimizer_ocr.timeout_seconds == 120


def test_load_runtime_settings_rejects_invalid_existing_file(tmp_path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "runtime_settings.json").write_text(
        json.dumps(
            {
                "schema_version": "bad",
                "interpreter": {"model": "", "max_output_tokens": 0},
                "normalizer": {"model": "gpt-5.4-mini", "max_output_tokens": "bad"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Runtime settings are invalid"):
        load_runtime_settings(state_dir)


def test_runtime_settings_loader_blocks_schema_error(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = state_module.RuntimeSettingsState().to_dict()
    (state_dir / "runtime_settings.json").write_text(json.dumps(state), encoding="utf-8")

    def _raise(_cls, _data):
        raise ValueError("bad schema")

    monkeypatch.setattr(state_module.RuntimeSettingsState, "from_dict", classmethod(_raise))

    with pytest.raises(ValueError, match="bad schema"):
        load_runtime_settings(state_dir)


def test_runtime_settings_loader_rejects_unknown_provider_id(tmp_path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = state_module.RuntimeSettingsState().to_dict()
    state["llm_shared_provider"]["provider_id"] = "unknown-provider"
    (state_dir / "runtime_settings.json").write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ValueError, match="llm_shared_provider.provider_id"):
        load_runtime_settings(state_dir)
