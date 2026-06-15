from __future__ import annotations

from normalizer_vision.assets import load_local_profile
from normalizer_vision.prompts import get_output_schema
from normalizer_vision.providers import OpenAIProvider


def test_openai_provider_builds_strict_payload(tmp_project_root):
    profile = load_local_profile(tmp_project_root, "housing.default.v1")
    schema = get_output_schema(profile)
    payload = OpenAIProvider.build_payload(
        model="gpt-5.4-mini",
        messages=[{"role": "user", "content": "hello"}],
        schema=schema,
        max_output_tokens=1000,
        thinking_effort="low",
    )
    assert payload["model"] == "gpt-5.4-mini"
    assert payload["input"][0]["content"][0]["type"] == "input_text"
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    assert "_source_refs" not in schema["properties"]["content"]["properties"]["fields"]["properties"]
    assert "_source_refs" not in schema["properties"]["content"]["properties"]["rows"]["items"]["properties"]
    assert "_units" in schema["properties"]["content"]["properties"]["rows"]["items"]["properties"]
    assert set(schema["properties"]["content"]["properties"]["rows"]["items"]["required"]) == set(
        schema["properties"]["content"]["properties"]["rows"]["items"]["properties"].keys()
    )


def test_openai_provider_builds_json_object_for_soft_schema():
    payload = OpenAIProvider.build_payload(
        model="gpt-5.4-mini",
        messages=[{"role": "user", "content": "hello"}],
        schema={"type": "object", "properties": {"ok": {"type": "string"}}},
        max_output_tokens=1000,
        thinking_effort="low",
    )
    assert payload["text"]["format"]["type"] == "json_object"


def test_output_schema_includes_operations_profile_enums(tmp_project_root, operations_profile_path):
    profile = load_local_profile(tmp_project_root, str(operations_profile_path))
    schema = get_output_schema(profile)
    classification = schema["properties"]["classification"]["properties"]
    content = schema["properties"]["content"]["properties"]
    row_properties = content["rows"]["items"]["properties"]

    assert "delivery_note" in classification["document_type"]["enum"]
    assert "operations" in classification["category"]["enum"]
    assert "recovery_plan" in classification["subcategory"]["enum"]
    assert "our_reference" in content["fields"]["properties"]
    assert "carrier_name" in content["fields"]["properties"]
    assert "position" in row_properties
    assert "participant_role" in row_properties
