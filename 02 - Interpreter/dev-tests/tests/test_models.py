"""Tests for shared model helpers."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from llm_interpreter.models import (
    DEFAULT_MAX_PAGE_ASSETS,
    DEFAULT_MAX_REQUEST_ASSET_BYTES,
    DEFAULT_MAX_WORKERS,
    InterpreterConfig,
    atomic_json_write,
    load_config,
    load_dotenv_file,
    read_env_file,
)


class TestAtomicJsonWrite:
    def test_parallel_writes_to_same_target_do_not_collide(self, tmp_path):
        target = tmp_path / "shared.json"

        def _write(index: int) -> None:
            atomic_json_write(target, {"index": index})

        for _round in range(10):
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(_write, index) for index in range(8)]
                for future in futures:
                    future.result()

        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload["index"] in range(8)
        assert not list(tmp_path.glob("*.tmp"))

    def test_temp_file_is_removed_after_replace_failures(self, tmp_path):
        target = tmp_path / "shared.json"

        with patch("llm_interpreter.models.serialization.os.replace", side_effect=PermissionError("locked")), patch(
            "llm_interpreter.models.serialization.time.sleep",
        ):
            with pytest.raises(PermissionError, match="locked"):
                atomic_json_write(target, {"index": 1})

        assert not list(tmp_path.glob("*.tmp"))

    def test_temp_file_is_removed_after_serialization_failures(self, tmp_path):
        target = tmp_path / "shared.json"

        with pytest.raises(TypeError):
            atomic_json_write(target, {"bad": object()})

        assert not list(tmp_path.glob("*.tmp"))

    def test_temp_prefix_stays_short_for_long_target_names(self, tmp_path, monkeypatch):
        target = tmp_path / ("x" * 120 + ".structured.json")
        captured: dict[str, str] = {}
        original_mkstemp = tempfile.mkstemp

        def _mkstemp(*args, **kwargs):
            captured["prefix"] = kwargs["prefix"]
            captured["suffix"] = kwargs["suffix"]
            return original_mkstemp(*args, **kwargs)

        monkeypatch.setattr("llm_interpreter.models.serialization.tempfile.mkstemp", _mkstemp)
        atomic_json_write(target, {"ok": True})

        assert target.exists()
        assert captured["prefix"] == "."
        assert captured["suffix"] == ".tmp"
        assert "x" * 25 not in captured["prefix"]


class TestLoadConfig:
    def test_model_settings_are_not_loaded_from_env(self):
        config = load_config({"LLM_MODEL": "gpt-4o", "MAX_OUTPUT_TOKENS": "123", "THINKING_EFFORT": "high"})
        assert config.model == "gpt-5.4"
        assert config.max_output_tokens == 8000
        assert config.thinking_effort == "no thinking"

    def test_invalid_ints_fail_closed_with_field_name(self):
        with pytest.raises(ValueError, match="MAX_RETRIES muss eine Ganzzahl sein"):
            load_config({"MAX_OUTPUT_TOKENS": "invalid", "MAX_RETRIES": "NaN"})

    def test_explicit_empty_env_mapping_does_not_fall_back_to_process_env(self):
        with patch.dict(os.environ, {"LLM_MODEL": "env-model"}, clear=True):
            config = load_config({})

        assert config.model == "gpt-5.4"

    def test_asset_limits_and_allowed_roots_are_loaded(self, tmp_path):
        env = {
            "MAX_PAGE_ASSETS": "9",
            "MAX_PAGE_ASSET_BYTES": "123",
            "MAX_REQUEST_ASSET_BYTES": "456",
            "PAGE_ASSET_ALLOWED_ROOTS": os.pathsep.join([str(tmp_path / "a"), str(tmp_path / "b")]),
        }
        config = load_config(env)

        assert config.max_page_assets == 9
        assert config.max_page_asset_bytes == 123
        assert config.max_request_asset_bytes == 456
        assert config.page_asset_allowed_roots == (
            (tmp_path / "a").resolve(strict=False),
            (tmp_path / "b").resolve(strict=False),
        )

    def test_debug_bundle_dir_and_worker_limit_are_loaded(self):
        config = load_config({"DEBUG_BUNDLE_DIR": r"C:\debug-bundles", "MAX_WORKERS": "5"})

        assert config.debug_bundle_dir == Path(r"C:\debug-bundles")
        assert config.max_workers == 5

    def test_default_limits_remain_visible(self):
        config = load_config({})

        assert config.max_page_assets == DEFAULT_MAX_PAGE_ASSETS
        assert config.max_request_asset_bytes == DEFAULT_MAX_REQUEST_ASSET_BYTES
        assert config.max_workers == DEFAULT_MAX_WORKERS

    def test_non_default_thinking_effort_is_rejected(self):
        with pytest.raises(ValueError, match="ungueltiges thinking_effort"):
            InterpreterConfig(thinking_effort="mid")


class TestEnvHelpers:
    def test_read_env_file_parses_key_values(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("LOG_LEVEL=DEBUG\nMAX_WORKERS=4\n", encoding="utf-8")

        assert read_env_file(env_path) == {"LOG_LEVEL": "DEBUG", "MAX_WORKERS": "4"}

    def test_load_dotenv_file_sets_missing_values_only_by_default(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("LOG_LEVEL=DEBUG\n", encoding="utf-8")
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}, clear=True):
            load_dotenv_file(env_path)
            assert os.environ["LOG_LEVEL"] == "INFO"

    def test_load_dotenv_file_can_override_existing_values(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("LOG_LEVEL=DEBUG\n", encoding="utf-8")
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}, clear=True):
            load_dotenv_file(env_path, override=True)
            assert os.environ["LOG_LEVEL"] == "DEBUG"

    def test_load_dotenv_file_respects_explicit_target_mapping(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("LOG_LEVEL=DEBUG\nMAX_WORKERS=4\n", encoding="utf-8")
        target: dict[str, str] = {}

        loaded = load_dotenv_file(env_path, environ=target)

        assert loaded == {"LOG_LEVEL": "DEBUG", "MAX_WORKERS": "4"}
        assert target == loaded

