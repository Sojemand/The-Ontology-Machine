from tests.edit_contract_shared import *  # noqa: F401,F403


def test_prompt_surfaces_roundtrip_preserves_base_and_delta_files(tmp_project_root: Path) -> None:
    bundle = _run_contract(tmp_project_root, {"action": "read_surface", "surface_id": "normalizer.prompt_bundle"})
    overrides = _run_contract(tmp_project_root, {"action": "read_surface", "surface_id": "normalizer.prompt_overrides"})

    override_value = dict(overrides["value"])
    override_value["system_prompt"] = "Override only"
    override_value["output_schema"] = '{"override":true}'
    bundle_value = dict(bundle["value"])
    bundle_value["user_task_intro"] = "Changed base intro"
    written_override = _run_contract(tmp_project_root, {"action": "write_surface", "surface_id": "normalizer.prompt_overrides", "value": override_value})
    written_bundle = _run_contract(tmp_project_root, {"action": "write_surface", "surface_id": "normalizer.prompt_bundle", "value": bundle_value})

    assert written_override["status"] == "ok"
    assert written_bundle["status"] == "ok"
    assert json.loads((tmp_project_root / "config" / "prompt_overrides.json").read_text(encoding="utf-8")) == {
        "system_prompt": "Override only",
        "output_schema": '{"override":true}',
    }
    assert json.loads((tmp_project_root / "config" / "prompt_bundle.json").read_text(encoding="utf-8"))["user_task_intro"] == "Changed base intro"


def test_taxonomy_release_draft_loads_verifies_and_writes_copy(tmp_project_root: Path) -> None:
    from normalizer_vision.edit_contract.taxonomy_release_draft import load_release_copy
    from normalizer_vision.semantic_release import build_semantic_release

    artifact_root = tmp_project_root / "Artifact Tree"
    release_path = artifact_root / "Semantic Release" / "releases" / "semantic_release.default" / "release.json"
    release_path.parent.mkdir(parents=True)
    release_path.write_text(json.dumps(build_semantic_release(tmp_project_root), indent=2), encoding="utf-8")

    draft = load_release_copy(artifact_root, release_path)
    draft["release"]["release_version"] = "manual.edit.v1"
    draft["release"]["projections"][0]["label"] = "Edited Projection"

    verified = _run_contract(
        tmp_project_root,
        {"action": "validate_surface", "surface_id": "normalizer.taxonomy_release_draft", "value": draft},
    )
    written = _run_contract(
        tmp_project_root,
        {"action": "write_surface", "surface_id": "normalizer.taxonomy_release_draft", "value": verified["value"]},
    )

    assert verified["status"] == "ok"
    assert verified["value"]["verification"]["status"] == "verified"
    assert verified["value"]["verification"]["db_decision"]["recommended_action"] == "select_current_db"
    assert verified["value"]["release"]["release_version"] == "manual.edit.v1"
    assert verified["value"]["release"]["release_fingerprint"] == verified["value"]["release"]["fingerprint"]

    written_path = Path(written["value"]["working_release_path"])
    assert written["status"] == "ok"
    assert written_path.exists()
    persisted = json.loads(written_path.read_text(encoding="utf-8"))
    assert persisted["release_version"] == "manual.edit.v1"
    assert persisted["runtime_semantic_assets"]["release_fingerprint"] == persisted["fingerprint"]


def test_source_package_surfaces_are_callable_but_not_in_public_bundle(tmp_project_root: Path) -> None:
    bundle = _run_contract(tmp_project_root, {"action": "read_bundle"})
    public_surface_ids = {item["surface_id"] for item in bundle["surfaces"]}
    for surface_id in (
        "normalizer.taxonomy_master",
        "normalizer.taxonomy_profiles",
        "normalizer.translation_glossary",
        "normalizer.semantic_release_authoring",
    ):
        result = _run_contract(tmp_project_root, {"action": "read_surface", "surface_id": surface_id})
        assert result["status"] == "ok"
        assert isinstance(result["value"], dict)
        assert surface_id not in public_surface_ids


def test_source_authoring_actions_are_edit_contract_actions(tmp_project_root: Path) -> None:
    result = _run_contract(tmp_project_root, {"action": "compile_release_package"})

    assert result["status"] == "ok"
    assert result["runtime_locale"] == "en"


def test_compile_release_package_still_validates_saved_normalizer_source_for_backend_flows(tmp_project_root: Path) -> None:
    compiled = source_operations.compile_release_package(tmp_project_root, {})

    assert compiled["status"] == "ok"
    assert compiled["runtime_locale"] == "en"
    assert compiled.get("artifacts") in (None, [])
