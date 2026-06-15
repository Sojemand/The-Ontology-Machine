from tests.edit_contract_shared import *  # noqa: F401,F403


def test_non_en_release_locale_is_rejected_without_creating_locale_files(tmp_project_root: Path) -> None:
    source_root = tmp_project_root / "config" / "taxonomy_sources" / "semantic_release.default"

    with pytest.raises(ValueError, match="en-only"):
        source_operations.export_semantic_release(
            tmp_project_root,
            {"target_locale": "fr"},
        )
    assert not (source_root / "master.text.fr.yaml").exists()
    assert not (source_root / "projections" / "finance.default.v1.text.fr.yaml").exists()

def test_review_actions_return_structured_review_payload_without_mutating_files(tmp_project_root: Path) -> None:
    source_root = tmp_project_root / "config" / "taxonomy_sources" / "semantic_release.default"
    master_text_path = source_root / "master.text.en.yaml"
    release_path = source_root / "release.yaml"
    before = {
        "master_text": master_text_path.read_text(encoding="utf-8"),
        "release": release_path.read_text(encoding="utf-8"),
    }
    bootstrap = source_operations.review_bootstrap_release(
        tmp_project_root,
        {
            "goal": "Route utility cost statements for housing documents safely and conservatively.",
            "must_keep": "issuer, document_date, tenant_share_heating_cost",
            "noise_tolerance": "medium",
        },
    )
    data_informed = source_operations.review_data_informed_release(
        tmp_project_root,
        {
            "structured_sample_path": str(REGRESSION_ROOT / "case_a.structured.json"),
            "expected_normalized_path": str(REGRESSION_ROOT / "case_a.expected.normalized.json"),
            "sample_label": "case-a",
        },
    )

    for response in (bootstrap, data_informed):
        _assert_hint_envelope(response)
        assert isinstance(response.get("review_payload"), dict)

    assert bootstrap["review_payload"]["review_mode"] == "bootstrap"
    assert bootstrap["review_payload"]["release_summary"]["candidate_fingerprint"]
    assert bootstrap["review_payload"]["routing_review"]["candidate_rankings"]
    assert isinstance(bootstrap["applied_changes"], list)
    assert bootstrap["changed_source_files"]
    assert sorted(bootstrap["review_payload"]["information_balance"]) == ["condensed", "kept", "lost"]
    assert data_informed["review_payload"]["review_mode"] == "data_informed"
    assert data_informed["review_payload"]["input_summary"]["sample_label"] == "case-a"
    assert data_informed["review_payload"]["document_comparison"]["original"]["status"] == "missing"
    assert data_informed["review_payload"]["document_comparison"]["normalized"]["summary"]["projection_id"] == "housing.default.v1"
    assert isinstance(data_informed["applied_changes"], list)
    assert data_informed["changed_source_files"]
    assert isinstance(data_informed["review_payload"]["next_steps"], list)
    after = {
        "master_text": master_text_path.read_text(encoding="utf-8"),
        "release": release_path.read_text(encoding="utf-8"),
    }
    assert after == before
