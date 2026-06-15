from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator_vision.models import load_config


def test_load_config_defaults_when_app_home_config_missing(monkeypatch: pytest.MonkeyPatch, scratch_dir: Path):
    monkeypatch.setattr("validator_vision.models.config.ensure_app_layout", lambda: scratch_dir)
    cfg = load_config()
    assert cfg.match.scalar_level == "FAIL"
    assert cfg.match.row_level == "WARN"
    assert cfg.match.skip_row_fields == ["_source_refs", "page", "sequence", "confidence"]
    assert "question" in cfg.match.row_anchor_keys


def test_load_config_rejects_missing_explicit_config(scratch_dir: Path):
    config_path = scratch_dir / "missing-selected-config.json"
    with pytest.raises(ValueError, match="Config nicht gefunden"):
        load_config(str(config_path))


def test_load_config_from_json(scratch_dir: Path):
    config_path = scratch_dir / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "checks": {"rows": False},
                "match": {"context_fields": ["custom_field"], "number_tolerance_absolute": 0.5},
                "max_issues_per_check": 5,
            }
        ),
        encoding="utf-8",
    )
    cfg = load_config(config_path)
    assert cfg.checks.rows is False
    assert cfg.match.context_fields == ["custom_field"]
    assert cfg.match.number_tolerance_absolute == 0.5
    assert cfg.max_issues_per_check == 5


def test_load_config_rejects_invalid_types(scratch_dir: Path):
    config_path = scratch_dir / "broken.json"
    config_path.write_text(json.dumps({"match": {"context_fields": "company"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="context_fields"):
        load_config(config_path)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"match": {"scalar_level": "INFO"}}, "scalar_level"),
        ({"match": {"row_level": "INFO"}}, "row_level"),
        ({"match": {"number_tolerance_absolute": -1}}, "number_tolerance_absolute"),
        ({"match": {"min_string_length": 0}}, "min_string_length"),
        ({"match": {"min_compact_length": 0}}, "min_compact_length"),
        ({"max_issues_per_check": 0}, "max_issues_per_check"),
    ],
)
def test_load_config_rejects_invalid_values(scratch_dir: Path, payload: dict, match: str):
    config_path = scratch_dir / "invalid.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=match):
        load_config(config_path)


def test_load_config_rejects_non_object_root(scratch_dir: Path):
    config_path = scratch_dir / "invalid.json"
    config_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="kein JSON-Objekt"):
        load_config(config_path)
