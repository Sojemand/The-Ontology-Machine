from tests.contract_stages_shared import *  # noqa: F401,F403

def test_workflow_healthcheck_does_not_require_local_fallback_profile(
    tmp_project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_project_root / "config" / "config.yaml").write_text(
        "taxonomy_profile_id: missing.local.profile\n",
        encoding="utf-8",
    )

    class DummyProvider:
        provider_name = "openai_oauth"

        def generate(self, *_args, **_kwargs) -> str:
            return '{"accepted":true}'

    monkeypatch.setattr(
        "normalizer_vision.orchestrator_contract.workflow.create_provider",
        lambda _config: DummyProvider(),
    )

    result = workflow.healthcheck(
        validation.HealthcheckCommand(runtime_settings=validation.RuntimeSettings(model="gpt-5.4", max_output_tokens=15000)),
        root=tmp_project_root,
    )

    assert result["status"] == "OK"
    assert result["healthy"] is True

def test_workflow_build_projection_catalog_returns_release_compiled_payload(tmp_project_root: Path):
    result = workflow.build_projection_catalog_response(root=tmp_project_root)

    assert result["status"] == "OK"
    assert result["projection_catalog"]["release_id"] == "semantic_release.default"
    assert result["projection_catalog"]["release_version"] == "2026-03-28.v6"
    assert result["projection_catalog"]["release_fingerprint"].startswith("sha256:")
    assert result["projection_catalog"]["master_taxonomy_id"] == "normalizer_taxonomy.master"
    assert result["projection_catalog"]["master_taxonomy_version"] == "2026-03-28.v6"
    assert [entry["projection_id"] for entry in result["projection_catalog"]["projections"]] == EXPECTED_DEFAULT_PROJECTION_IDS

def test_validation_rejects_unknown_fields_for_build_projection_catalog():
    with pytest.raises(ValueError, match="Unbekannte Felder: output_path"):
        validation.require_action({"action": "build_projection_catalog", "output_path": "catalog.json"})

def test_validation_accepts_build_runtime_semantic_assets_release(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)

    command = validation.parse_build_runtime_semantic_assets_command(
        {"action": "build_runtime_semantic_assets", "release": release}
    )

    assert command.release["release_id"] == "semantic_release.default"

def test_validation_rejects_missing_build_runtime_semantic_assets_release():
    with pytest.raises(ValueError, match="release muss ein JSON-Objekt sein"):
        validation.parse_build_runtime_semantic_assets_command({"action": "build_runtime_semantic_assets"})

def test_validation_rejects_non_object_build_runtime_semantic_assets_release():
    with pytest.raises(ValueError, match="release muss ein JSON-Objekt sein"):
        validation.parse_build_runtime_semantic_assets_command(
            {"action": "build_runtime_semantic_assets", "release": []}
        )

def test_validation_rejects_runtime_settings_for_build_runtime_semantic_assets(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)

    with pytest.raises(ValueError, match="keine runtime_settings"):
        validation.parse_build_runtime_semantic_assets_command(
            {
                "action": "build_runtime_semantic_assets",
                "release": release,
                "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
            }
        )

def test_validation_rejects_unknown_fields_for_build_runtime_semantic_assets(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)

    with pytest.raises(ValueError, match="Unbekannte Felder: output_path"):
        validation.parse_build_runtime_semantic_assets_command(
            {
                "action": "build_runtime_semantic_assets",
                "release": release,
                "output_path": "C:/tmp/runtime_semantic_assets.json",
            }
        )

def test_workflow_build_runtime_semantic_assets_returns_bundle(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)

    result = workflow.build_runtime_semantic_assets_response(
        validation.BuildRuntimeSemanticAssetsCommand(release=release)
    )

    assert result["status"] == "OK"
    assert result["runtime_semantic_assets"]["schema_version"] == "runtime_semantic_assets_v1"
    assert result["runtime_semantic_assets"]["release_fingerprint"] == release["fingerprint"]

def test_validation_accepts_publish_semantic_release_without_runtime_settings():
    assert validation.parse_publish_semantic_release_command({"action": "publish_semantic_release"}) == validation.PublishSemanticReleaseCommand()

def test_validation_accepts_publish_semantic_release_output_path(tmp_path: Path):
    output_path = tmp_path / "custom.release.json"

    assert validation.parse_publish_semantic_release_command(
        {"action": "publish_semantic_release", "output_path": str(output_path)}
    ) == validation.PublishSemanticReleaseCommand(output_path=output_path)

def test_validation_accepts_publish_semantic_release_target_locale() -> None:
    assert validation.parse_publish_semantic_release_command(
        {"action": "publish_semantic_release", "target_locale": "en"}
    ) == validation.PublishSemanticReleaseCommand(target_locale="en")

def test_validation_accepts_list_default_blueprints_without_runtime_settings() -> None:
    assert validation.parse_list_default_blueprints_command({"action": "list_default_blueprints"}) is None

def test_validation_accepts_export_default_blueprint_release_output_path(tmp_path: Path) -> None:
    output_path = tmp_path / "default.release.json"

    assert validation.parse_export_default_blueprint_release_command(
        {
            "action": "export_default_blueprint_release",
            "blueprint_ref": "default",
            "output_path": str(output_path),
        }
    ) == validation.ExportDefaultBlueprintReleaseCommand(
        blueprint_ref="default",
        output_path=output_path,
    )

def test_validation_accepts_export_default_blueprint_release_target_locale(tmp_path: Path) -> None:
    output_path = tmp_path / "default-en.release.json"

    assert validation.parse_export_default_blueprint_release_command(
        {
            "action": "export_default_blueprint_release",
            "blueprint_ref": "default",
            "target_locale": "en",
            "output_path": str(output_path),
        }
    ) == validation.ExportDefaultBlueprintReleaseCommand(
        blueprint_ref="default",
        target_locale="en",
        output_path=output_path,
    )

def test_validation_rejects_export_default_blueprint_release_without_blueprint_ref() -> None:
    with pytest.raises(ValueError, match="blueprint_ref fehlt oder ist ungueltig"):
        validation.parse_export_default_blueprint_release_command(
            {
                "action": "export_default_blueprint_release",
                "output_path": "C:/tmp/default-en.release.json",
            }
        )

def test_validation_accepts_create_zero_shot_working_release(tmp_path: Path) -> None:
    output_path = tmp_path / "zero.release.json"

    assert validation.parse_create_zero_shot_working_release_command(
        {
            "action": "create_zero_shot_working_release",
            "blueprint_ref": "default",
            "target_release_id": "semantic_release.test",
            "target_release_version": "v1",
            "target_locale": "en",
            "output_path": str(output_path),
        }
    ) == validation.CreateZeroShotWorkingReleaseCommand(
        blueprint_ref="default",
        target_release_id="semantic_release.test",
        target_release_version="v1",
        target_locale="en",
        output_path=output_path,
    )
