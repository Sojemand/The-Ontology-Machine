from __future__ import annotations

from normalizer_vision.prompts import build_messages
from normalizer_vision.prompts.validation import get_output_schema

from .prompts_creative_profile import creative_story_profile


def test_dynamic_promotion_contract_marks_multi_fields_as_arrays(sample_structured_input):
    profile = creative_story_profile()
    messages = build_messages(sample_structured_input, profile)
    text = messages[1]["content"]

    assert "content.fields.theme -> document_themes | cardinality=multi | value_type=string" in text
    assert "content.fields.story_title -> document_story_title | cardinality=single | value_type=string" in text
    assert '"theme": [' in text
    assert "row.description" in text
    assert "Heating cost statement" not in text


def test_profile_schema_uses_array_for_multi_promotion_fields():
    profile = creative_story_profile()
    schema = get_output_schema(profile)
    fields = schema["properties"]["content"]["properties"]["fields"]["properties"]

    assert fields["theme"]["type"] == ["array", "null"]
    assert fields["theme"]["items"]["type"] == ["string"]
    assert fields["story_title"]["type"] == ["string", "null"]
