from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from llm_interpreter.prompts import get_output_schema, get_persisted_output_schema, load_prompt_bundle
from llm_interpreter.prompts.bundle import default_prompt_bundle


def test_output_schemas_fix_processing_profile_to_vision() -> None:
    for schema in (get_output_schema(), get_persisted_output_schema()):
        processing = schema["properties"]["processing"]
        assert "interpreter_profile" in processing["required"]
        assert processing["properties"]["interpreter_profile"] == {
            "type": "string",
            "enum": ["vision", "file"],
        }


def test_persisted_output_schema_requires_source() -> None:
    schema = get_persisted_output_schema()
    assert "source" in schema["required"]


def test_output_schema_requires_segments_with_optional_function() -> None:
    schema = get_output_schema()
    content = schema["properties"]["content"]
    assert "segments" in content["required"]
    segment_schema = content["properties"]["segments"]["items"]
    assert segment_schema["required"] == ["segment_id", "unit_kind", "page", "sequence", "text"]
    assert segment_schema["properties"]["function"] == {"type": ["string", "null"]}
    assert "_source_refs" not in segment_schema["properties"]


def test_load_prompt_bundle_uses_defaults_and_rejects_partial_bundle(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    monkeypatch.setenv("INTERPRETER_HOME", str(tmp_path))

    payload = load_prompt_bundle()
    assert payload["system_prompt_md"].startswith("You extract structured data from documents.")
    assert payload["output_schema_json"] == json.dumps(get_output_schema(), indent=2, ensure_ascii=False)

    bundle_dir = config_dir / "prompt_bundle"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "system_prompt.md").write_text("system", encoding="utf-8")

    with pytest.raises(ValueError, match="Prompt-Bundle unvollstaendig"):
        load_prompt_bundle()


def test_reference_policy_module_was_removed() -> None:
    reference_policy = Path(__file__).parent.parent.parent / "llm_interpreter" / "prompts" / "reference_policy.py"
    assert not reference_policy.exists()


def test_file_profile_uses_merged_canonical_schema() -> None:
    processing = get_output_schema()["properties"]["processing"]
    assert processing["properties"]["interpreter_profile"]["enum"] == ["vision", "file"]


def test_load_prompt_bundle_heals_saved_schema_drift_for_file_profile(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    bundle_dir = config_dir / "prompt_bundle"
    bundle_dir.mkdir(parents=True)
    payload = default_prompt_bundle()
    drifted_schema = get_output_schema()
    drifted_schema["properties"]["processing"]["properties"]["interpreter_profile"] = {
        "type": "string",
        "enum": ["file"],
    }
    for key, filename in {
        "system_prompt_md": "system_prompt.md",
        "user_prompt_rules_md": "user_prompt_rules.md",
        "output_schema_json": "output_schema.json",
        "projection_hint_policy_md": "projection_hint_policy.md",
    }.items():
        value = json.dumps(drifted_schema, indent=2, ensure_ascii=False) if key == "output_schema_json" else payload[key]
        (bundle_dir / filename).write_text(value, encoding="utf-8")
    monkeypatch.setenv("INTERPRETER_HOME", str(tmp_path))

    loaded = load_prompt_bundle()

    canonical = json.dumps(get_output_schema(), indent=2, ensure_ascii=False)
    assert loaded["output_schema_json"] == canonical
    assert json.loads((bundle_dir / "output_schema.json").read_text(encoding="utf-8")) == get_output_schema()
