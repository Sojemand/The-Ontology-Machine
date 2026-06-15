from __future__ import annotations

import json
from pathlib import Path

from normalizer_vision.assets import load_local_profile
from normalizer_vision.prompts import PromptBundle, build_messages, get_output_schema_text, load_prompt_bundle


def test_output_schema_text_prefers_prompt_bundle_override():
    text = get_output_schema_text("housing.default.v1", PromptBundle(prompts={"output_schema": '{"custom":true}'}))
    assert text == '{"custom":true}'


def test_load_prompt_bundle_merges_base_bundle_and_delta_overrides(tmp_project_root):
    bundle_path = tmp_project_root / "config" / "prompt_bundle.json"
    overrides_path = tmp_project_root / "config" / "prompt_overrides.json"
    overrides_path.write_text(
        json.dumps(
            {
                "system_prompt": "Override system prompt",
                "output_schema": '{"custom":true}',
            }
        ),
        encoding="utf-8",
    )

    bundle = load_prompt_bundle(bundle_path, overrides_path)

    assert bundle.get("system_prompt", "") == "Override system prompt"
    assert bundle.get("user_task_intro", "").startswith("Task for this run")
    assert bundle.output_schema_text("housing.default.v1") == '{"custom":true}'


def test_build_messages_uses_prompt_bundle_file_content(tmp_project_root, sample_structured_input):
    profile = load_local_profile(tmp_project_root, "housing.default.v1")
    (tmp_project_root / "config" / "prompt_bundle.json").write_text(
        json.dumps(
            {
                "system_prompt": "Custom base system prompt",
                "user_task_intro": "Custom task intro",
                "user_quality_rules": "Custom quality rules",
                "output_schema": "{\"base\":true}",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_project_root / "config" / "prompt_overrides.json").write_text(
        json.dumps({"user_task_intro": "Override intro"}, ensure_ascii=False),
        encoding="utf-8",
    )

    messages = build_messages(
        sample_structured_input,
        profile,
        load_prompt_bundle(
            tmp_project_root / "config" / "prompt_bundle.json",
            tmp_project_root / "config" / "prompt_overrides.json",
        ),
    )

    assert messages[0]["content"] == "Custom base system prompt"
    assert "Override intro" in messages[1]["content"]
    assert "Custom quality rules" in messages[1]["content"]
    assert '{"base":true}' in messages[1]["content"]


def test_checked_in_prompt_bundle_matches_default_contract_payload():
    bundle_path = Path(__file__).resolve().parents[2] / "config" / "prompt_bundle.json"
    checked_in_bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert "1 to 3 short, information-dense English sentences" in checked_in_bundle["system_prompt"]
    assert '"page of", "the page shows", or "Page X of Y"' in checked_in_bundle["system_prompt"]
    assert '"page of", "the page shows", or "Page X of Y"' in checked_in_bundle["user_quality_rules"]
    assert "visible document role or topic plus 1 to 3 concrete anchors" in checked_in_bundle["user_quality_rules"]
    assert "Apply domain-specific normalization only when the active Semantic Release" in checked_in_bundle["system_prompt"]
    assert "do not apply hidden business, finance, housing, legal, narrative, or other domain assumptions" in checked_in_bundle["system_prompt"]
    assert "Fill nullable compatibility fields only when supported" in checked_in_bundle["user_quality_rules"]
    assert '"description": "Compact evidence-bound English semantic summary of the document function or topic and its strongest visible anchors."' in checked_in_bundle["output_schema"]
