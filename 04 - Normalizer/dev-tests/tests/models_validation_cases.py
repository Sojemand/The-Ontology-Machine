from __future__ import annotations

from pathlib import Path

import pytest

from normalizer_vision.models import NormalizerProjectConfig, NormalizerRuntimeSettings, load_config


def test_load_config_ignores_process_environment(tmp_project_root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VISION_OPENAI_AUTH_MODE", "api_keys")
    monkeypatch.setenv("VISION_OPENAI_API_KEY", "sk-runtime")
    monkeypatch.setenv("NORMALIZER_OPENAI_API_KEY", "sk-process")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-global")
    monkeypatch.setenv("NORMALIZER_MODEL", "gpt-4.1")

    config = load_config(tmp_project_root)

    assert not hasattr(config, "api_key")
    assert not hasattr(config, "model")
    assert config.taxonomy_profile_id == "housing.default.v1"


def test_load_config_rejects_external_asset_paths(tmp_project_root: Path):
    config_path = tmp_project_root / "config" / "config.yaml"
    config_path.write_text(
        "taxonomy_profile_path: ..\\outside.json\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="taxonomy_profile_path"):
        load_config(tmp_project_root)


def test_load_config_rejects_parent_segment_config_path(tmp_project_root: Path):
    with pytest.raises(ValueError, match="config_path"):
        load_config(tmp_project_root, Path("..\\outside.yaml"))


def test_load_config_rejects_absolute_config_path_outside_module(tmp_project_root: Path, tmp_path: Path):
    external_path = tmp_path / "outside-config.yaml"
    external_path.write_text("taxonomy_profile_id: operations.default.v1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="config_path"):
        load_config(tmp_project_root, external_path)


def test_load_config_rejects_invalid_provider(tmp_project_root: Path):
    config_path = tmp_project_root / "config" / "config.yaml"
    config_path.write_text("provider: azure\n", encoding="utf-8")

    with pytest.raises(ValueError, match="provider"):
        load_config(tmp_project_root)


def test_load_config_rejects_unknown_top_level_fields(tmp_project_root: Path):
    config_path = tmp_project_root / "config" / "config.yaml"
    config_path.write_text("timeout_seconds: 300\nmystery_knob: true\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mystery_knob"):
        load_config(tmp_project_root)


def test_load_config_validates_projection_routing(tmp_project_root: Path):
    config_path = tmp_project_root / "config" / "config.yaml"
    config_path.write_text(
        "timeout_seconds: 300\nprojection_routing:\n  hint_confidence_low_threshold: 0.9\n  hint_confidence_medium_threshold: 0.8\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="thresholds"):
        load_config(tmp_project_root)


def test_load_config_rejects_invalid_numeric_values(tmp_project_root: Path):
    config_path = tmp_project_root / "config" / "config.yaml"
    config_path.write_text("timeout_seconds: 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="timeout_seconds"):
        load_config(tmp_project_root)


def test_load_config_rejects_removed_auth_fields(tmp_project_root: Path):
    config_path = tmp_project_root / "config" / "config.yaml"
    config_path.write_text("api_base_url: https://api.openai.com/v1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="api_base_url"):
        load_config(tmp_project_root)


@pytest.mark.parametrize("key", ["model", "max_output_tokens", "thinking_effort"])
def test_load_config_rejects_removed_runtime_fields(tmp_project_root: Path, key: str):
    config_path = tmp_project_root / "config" / "config.yaml"
    value = {"model": "gpt-5.4", "max_output_tokens": "15000", "thinking_effort": "no thinking"}[key]
    config_path.write_text(f"{key}: {value}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Modell-Ownership"):
        load_config(tmp_project_root)


def test_project_config_rejects_default_workers_above_batch_worker_limit():
    with pytest.raises(ValueError, match="default_workers"):
        NormalizerProjectConfig(default_workers=5, max_batch_workers=4)


def test_project_config_rejects_invalid_projection_hint_mode():
    with pytest.raises(ValueError, match="projection_hint_mode"):
        NormalizerProjectConfig(projection_hint_mode="maybe")


def test_runtime_settings_reject_invalid_max_output_tokens():
    with pytest.raises(ValueError, match="runtime_settings.max_output_tokens"):
        NormalizerRuntimeSettings(model="gpt-5.4-mini", max_output_tokens=0)
