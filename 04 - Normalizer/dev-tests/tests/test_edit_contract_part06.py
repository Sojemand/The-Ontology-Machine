from tests.edit_contract_shared import *  # noqa: F401,F403


def test_generate_locale_translation_payload_action_is_not_exposed(tmp_project_root: Path) -> None:
    response = _run_contract(
        tmp_project_root,
        {
            "action": "generate_locale_translation_payload",
            "source_locale": "en",
            "target_locale": "es",
            "model": "gpt-5.4-mini",
            "max_output_tokens": 16000,
        },
    )

    assert response["status"] == "error"
    assert "Unbekannte" in response["reason"]
