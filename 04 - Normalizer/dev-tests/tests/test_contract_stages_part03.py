from tests.contract_stages_shared import *  # noqa: F401,F403

def test_workflow_create_zero_shot_working_release_exports_blueprint(tmp_project_root: Path) -> None:
    output_path = tmp_project_root / "output" / "zero.release.json"

    result = workflow.create_zero_shot_working_release_response(
        validation.CreateZeroShotWorkingReleaseCommand(
            blueprint_ref="default",
                target_locale="en",
            output_path=output_path,
        ),
        root=tmp_project_root,
    )

    assert result["status"] == "OK"
    assert result["blueprint_ref"] == "default"
    assert result["output_path"] == str(output_path)
    assert output_path.exists()

def test_workflow_list_default_blueprints_returns_checked_in_defaults(tmp_project_root: Path) -> None:
    result = workflow.list_default_blueprints_response(root=tmp_project_root)

    assert result["status"] == "OK"
    assert [item["blueprint_ref"] for item in result["blueprints"]] == ["default"]
    assert result["blueprints"][0]["primary_locale"] == "en"
    assert result["blueprints"][0]["default_runtime_locale"] == "en"

def test_workflow_export_default_blueprint_release_writes_selected_blueprint_release(tmp_project_root: Path) -> None:
    output_path = tmp_project_root / "output" / "default.release.json"

    result = workflow.export_default_blueprint_release_response(
        validation.ExportDefaultBlueprintReleaseCommand(
            blueprint_ref="default",
            output_path=output_path,
        ),
        root=tmp_project_root,
    )

    assert result["status"] == "OK"
    assert result["blueprint_ref"] == "default"
    assert result["output_path"] == str(output_path)
    assert result["runtime_locale"] == "en"
    assert output_path.exists()

def test_workflow_export_default_blueprint_release_respects_target_locale(tmp_project_root: Path) -> None:
    output_path = tmp_project_root / "output" / "default-en.release.json"

    result = workflow.export_default_blueprint_release_response(
        validation.ExportDefaultBlueprintReleaseCommand(
            blueprint_ref="default",
            target_locale="en",
            output_path=output_path,
        ),
        root=tmp_project_root,
    )

    assert result["status"] == "OK"
    assert result["blueprint_ref"] == "default"
    assert result["output_path"] == str(output_path)
    assert result["runtime_locale"] == "en"
    assert output_path.exists()

def test_validation_rejects_runtime_settings_for_publish_semantic_release():
    with pytest.raises(ValueError, match="keine runtime_settings"):
        validation.parse_publish_semantic_release_command(
            {
                "action": "publish_semantic_release",
                "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
            }
        )

def test_validation_rejects_unknown_fields_for_publish_semantic_release():
    with pytest.raises(ValueError, match="Unbekannte Felder: extra"):
        validation.parse_publish_semantic_release_command({"action": "publish_semantic_release", "extra": True})

def test_validation_rejects_publish_output_path_directory(tmp_path: Path):
    target_dir = tmp_path / "release-dir"
    target_dir.mkdir()

    with pytest.raises(ValueError, match="output_path darf kein Verzeichnis sein"):
        validation.parse_publish_semantic_release_command(
            {"action": "publish_semantic_release", "output_path": str(target_dir)}
        )

def test_workflow_publish_semantic_release_uses_recipe_defaults(tmp_project_root: Path):
    result = workflow.publish_semantic_release_response(validation.PublishSemanticReleaseCommand(), root=tmp_project_root)

    assert result["status"] == "OK"
    assert result["output_path"].endswith("output\\semantic_release.default__2026-03-28.v6__en.json")
    assert result["release_id"] == "semantic_release.default"
    assert result["release_version"] == "2026-03-28.v6"
    assert result["projection_ids"] == EXPECTED_DEFAULT_PROJECTION_IDS
    assert result["fingerprint"].startswith("sha256:")
    assert result["runtime_locale"] == "en"
    assert result["master_taxonomy_release_id"].startswith("sha256:")

def test_workflow_publish_semantic_release_respects_explicit_output_path(tmp_project_root: Path):
    output_path = tmp_project_root / "output" / "custom.release.json"
    result = workflow.publish_semantic_release_response(
        validation.PublishSemanticReleaseCommand(output_path=output_path),
        root=tmp_project_root,
    )

    assert result["status"] == "OK"
    assert result["output_path"] == str(output_path)
    assert output_path.exists()

def test_workflow_publish_semantic_release_accepts_target_locale(tmp_project_root: Path):
    result = workflow.publish_semantic_release_response(
        validation.PublishSemanticReleaseCommand(target_locale="en"),
        root=tmp_project_root,
    )

    assert result["status"] == "OK"
    assert result["output_path"].endswith("output\\semantic_release.default__2026-03-28.v6__en.json")
    assert result["runtime_locale"] == "en"
    assert result["master_taxonomy_release_id"].startswith("sha256:")

def test_adapter_load_request_rejects_non_object_root(tmp_path: Path):
    request_path = tmp_path / "request.json"
    request_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON-Objekt"):
        adapter.load_request(request_path)

def test_validation_rejects_missing_structured_path():
    with pytest.raises(ValueError, match="structured_path fehlt oder ist ungueltig"):
        validation.parse_normalize_document_command({"action": "normalize_document", "normalized_output_path": "x"})

def test_validation_rejects_legacy_output_dir_field(tmp_path: Path):
    structured_path = tmp_path / "doc.structured.json"
    structured_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="output_dir wird nicht mehr akzeptiert"):
        validation.parse_normalize_document_command(
            {
                "action": "normalize_document",
                "structured_path": str(structured_path),
                "output_dir": str(tmp_path / "normalized"),
                "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000},
            }
        )

def test_validation_rejects_normalized_output_path_when_it_is_a_directory(tmp_path: Path):
    structured_path = tmp_path / "doc.structured.json"
    structured_path.write_text("{}", encoding="utf-8")
    target_dir = tmp_path / "normalized"
    target_dir.mkdir()

    with pytest.raises(ValueError, match="normalized_output_path darf kein Verzeichnis sein"):
        validation.parse_normalize_document_command(
            {
                "action": "normalize_document",
                "structured_path": str(structured_path),
                "normalized_output_path": str(target_dir),
                "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000},
            }
        )

def test_validation_rejects_structured_path_without_structured_json_suffix(tmp_path: Path):
    structured_path = tmp_path / "doc.json"
    structured_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match=r"structured_path muss auf \*\.structured\.json enden"):
        validation.parse_normalize_document_command(
            {
                "action": "normalize_document",
                "structured_path": str(structured_path),
                "normalized_output_path": str(tmp_path / "normalized" / "doc.structured.normalized.json"),
                "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 12000},
            }
        )
