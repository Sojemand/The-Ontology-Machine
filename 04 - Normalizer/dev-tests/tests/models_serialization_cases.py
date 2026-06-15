from __future__ import annotations

from datetime import datetime
import json
import tempfile
from pathlib import Path

import pytest

from normalizer_vision.models import NormalizerRuntimeSettings, atomic_json_write
import normalizer_vision.models.serialization as serialization
from normalizer_vision.models.coercion import (
    coerce_bool,
    coerce_float,
    coerce_int,
    coerce_string,
    dedupe_keep_order,
    string_list,
)
from normalizer_vision.models.serialization import to_json_compatible


def test_atomic_json_write_roundtrip(tmp_path: Path):
    path = tmp_path / "out.json"
    atomic_json_write(path, {"hello": "world"})
    assert json.loads(path.read_text(encoding="utf-8")) == {"hello": "world"}
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_json_write_uses_tiny_temp_name_for_path_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / ("x" * 120 + ".structured.normalized.json")
    captured: dict[str, str] = {}
    original_mkstemp = tempfile.mkstemp

    def _mkstemp(*args, **kwargs):
        captured["prefix"] = kwargs["prefix"]
        captured["suffix"] = kwargs["suffix"]
        return original_mkstemp(*args, **kwargs)

    monkeypatch.setattr(serialization.tempfile, "mkstemp", _mkstemp)
    atomic_json_write(path, {"hello": "world"})

    assert path.exists()
    assert captured["prefix"] == ".t."
    assert captured["suffix"] == ".tmp"
    assert len(captured["prefix"] + "12345678" + captured["suffix"]) < len(path.name)


def test_atomic_json_write_flushes_before_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: list[int] = []

    monkeypatch.setattr(serialization.os, "fsync", lambda file_number: calls.append(file_number))

    atomic_json_write(tmp_path / "out.json", {"hello": "world"})

    assert calls


def test_runtime_settings_use_fixed_thinking_mapping():
    settings = NormalizerRuntimeSettings(model="gpt-5.4-mini", max_output_tokens=15_000)

    assert settings.thinking_effort == "no thinking"
    assert settings.api_thinking_effort == "none"


def test_to_json_compatible_handles_nested_python_values(tmp_path: Path):
    payload = {
        "when": datetime(2026, 3, 24, 15, 4, 5),
        "path": tmp_path / "data.json",
        "items": {"flags": {True, False}, "values": (1, 2, 3)},
    }

    result = to_json_compatible(payload)

    assert result["when"] == "2026-03-24T15:04:05"
    assert result["path"] == str(tmp_path / "data.json")
    assert sorted(result["items"]["flags"]) == [False, True]
    assert result["items"]["values"] == [1, 2, 3]


def test_shared_scalar_helpers_preserve_expected_normalization():
    assert coerce_bool("ja", False) is True
    assert coerce_float("12,5", 0.0) == 12.5
    assert coerce_int("12,0", 0) == 12
    assert coerce_string("  test  ", normalize=str.upper) == "TEST"
    assert string_list([" eins ", None, 2], normalize=str.strip) == ["eins", "2"]
    assert dedupe_keep_order(["a", "b", "a", "c"]) == ["a", "b", "c"]


def test_to_json_compatible_rejects_unknown_types():
    class Unsupported:
        pass

    with pytest.raises(TypeError, match="Nicht JSON-serialisierbarer Wert"):
        to_json_compatible(Unsupported())
