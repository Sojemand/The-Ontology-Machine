from tests.edit_contract_shared import *  # noqa: F401,F403


def test_describe_surfaces_returns_release_draft_only_for_taxonomy_authoring(tmp_project_root: Path) -> None:
    payload = _run_contract(tmp_project_root, {"action": "describe_surfaces"})

    assert payload["status"] == "ok"
    assert payload["module_summary"].startswith("NORMALIZER HELP")
    assert "config/taxonomy_sources/<release_id>/" not in payload["module_summary"]
    assert "Blueprint" not in payload["module_summary"]
    assert "Create Projection Draft" not in payload["module_summary"]
    assert "Taxonomy / Projection Release" in payload["module_summary"]
    assert [surface["surface_id"] for surface in payload["surfaces"]] == [
        "normalizer.settings",
        "normalizer.prompt_overrides",
        "normalizer.prompt_bundle",
        "normalizer.taxonomy_release_draft",
        "normalizer.debug_capabilities",
    ]

    release_draft = payload["surfaces"][3]
    assert release_draft["editor_kind"] == "taxonomy_release_draft"
    assert release_draft["storage_kind"] == "semantic_release_copy"
    assert release_draft["drift_status"] == "working_copy"
    assert release_draft["validate_label"] == "Verify"
    assert release_draft["save_label"] == "Write Copy"
    assert release_draft["editor_metadata"]["release_search"] == "recursive_release_json"
    assert release_draft["editor_metadata"]["copy_policy"] == "never_mutate_origin"
    assert "find_semantic_releases" in release_draft["editor_metadata"]["tool_catalog"]
    assert "verify_release" in release_draft["editor_metadata"]["tool_catalog"]

    debug_actions = [link["action"] for link in payload["surfaces"][-1]["operation_links"]]
    assert "normalize_document" in debug_actions
    assert "build_runtime_semantic_assets" in debug_actions


def test_settings_surface_roundtrip_persists_nested_projection_routing(tmp_project_root: Path) -> None:
    current = _run_contract(tmp_project_root, {"action": "read_surface", "surface_id": "normalizer.settings"})

    assert current["status"] == "ok"
    updated = dict(current["value"])
    updated["default_workers"] = 2
    updated["projection_routing.hint_confidence_high_bonus"] = 4
    updated["projection_routing.hint_reject_margin"] = 5
    updated["projection_routing.field_signal_limit"] = 6
    written = _run_contract(tmp_project_root, {"action": "write_surface", "surface_id": "normalizer.settings", "value": updated})
    reread = _run_contract(tmp_project_root, {"action": "read_surface", "surface_id": "normalizer.settings"})

    assert written["status"] == "ok"
    assert reread["value"]["default_workers"] == 2
    config_payload = yaml.safe_load((tmp_project_root / "config" / "config.yaml").read_text(encoding="utf-8"))
    assert config_payload["default_workers"] == 2
    assert config_payload["projection_routing"]["field_signal_limit"] == 6
    assert config_payload["projection_routing"]["hint_confidence_high_bonus"] == 4
