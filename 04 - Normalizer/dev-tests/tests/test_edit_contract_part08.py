from tests.edit_contract_shared import *  # noqa: F401,F403

def test_review_actions_validate_inputs(tmp_project_root: Path) -> None:
    invalid_json_path = tmp_project_root / "invalid.expected.normalized.json"
    invalid_json_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="noise_tolerance"):
        source_operations.review_bootstrap_release(
            tmp_project_root,
            {
                "goal": "Zielaussage",
                "must_keep": "issuer",
                "noise_tolerance": "extreme",
            },
        )
    with pytest.raises(ValueError, match="expected_normalized_path"):
        source_operations.review_data_informed_release(
            tmp_project_root,
            {
                "structured_sample_path": str(REGRESSION_ROOT / "case_a.structured.json"),
                "expected_normalized_path": str(tmp_project_root / "missing.json"),
            },
        )
    with pytest.raises(ValueError, match="JSON root|JSON-Objekt"):
        source_operations.review_data_informed_release(
            tmp_project_root,
            {
                "structured_sample_path": str(REGRESSION_ROOT / "case_a.structured.json"),
                "expected_normalized_path": str(invalid_json_path),
            },
        )

def test_apply_actions_persist_source_without_materializing_legacy_compatibility_files(tmp_project_root: Path) -> None:
    source_root = tmp_project_root / "config" / "taxonomy_sources" / "semantic_release.default"
    master_text_path = source_root / "master.text.en.yaml"
    release_path = source_root / "release.yaml"

    bootstrap = source_operations.bootstrap_release_package(
        tmp_project_root,
        {
            "goal": "Route documents for housing meetings and utility costs safely.",
            "must_keep": "issuer, custom_energy_case",
            "noise_tolerance": "low",
        },
    )
    unknown_normalized_path = tmp_project_root / "expected.custom.normalized.json"
    unknown_normalized_path.write_text(
        json.dumps(
            {
                "classification": {"document_type": "utility_cost_statement", "category": "finance", "subcategory": "utilities"},
                "content": {
                    "structure": {"columns": ["custom_energy_metric"], "form_fields": ["issuer"]},
                    "fields": {"issuer": "Acme"},
                    "rows": [{"_row_type": "custom_energy_row", "custom_energy_metric": 1.23}],
                },
                "projection": {"projection_id": "housing.custom_energy.default.v1", "selection": {"reason": "sample-fit"}},
            }
        ),
        encoding="utf-8",
    )
    refined = source_operations.refine_release_package(
        tmp_project_root,
        {
            "structured_sample_path": str(REGRESSION_ROOT / "case_a.structured.json"),
            "expected_normalized_path": str(unknown_normalized_path),
            "sample_label": "custom-case",
        },
    )

    master_text = yaml.safe_load(master_text_path.read_text(encoding="utf-8"))
    release_yaml = yaml.safe_load(release_path.read_text(encoding="utf-8"))

    assert bootstrap["status"] == "ok"
    assert refined["status"] == "ok"
    assert bootstrap["review_payload"]["review_mode"] == "bootstrap"
    assert refined["review_payload"]["review_mode"] == "data_informed"
    assert bootstrap["applied_changes"]
    assert refined["applied_changes"]
    assert not any((tmp_project_root / "config").glob("normalizer_taxonomy.*.json"))
    assert "custom_energy_case" in master_text["field_codes"]
    assert "housing.custom_energy.default.v1" in release_yaml["projection_ids"]
    assert release_yaml["governance"]["source_package_blanket_exception"]["projection_count"] == len(release_yaml["projection_ids"])
    assert release_yaml["governance"]["source_package_blanket_exception"]["allowed_file_count"] == len(
        release_yaml["governance"]["source_package_blanket_exception"]["files"]
    )

def test_export_semantic_release_validates_and_compiles_before_publish(monkeypatch, tmp_project_root: Path) -> None:
    export_path = tmp_project_root / "output" / "semantic_release.exported.json"
    steps: list[object] = []

    monkeypatch.setattr(
        source_operations,
        "validate_release_package",
        lambda root: steps.append(("validate", root)) or {"status": "ok"},
    )
    monkeypatch.setattr(
        source_operations,
        "ensure_compiled_taxonomy_assets",
        lambda root: steps.append(("compile", root)) or SimpleNamespace(release={"projection_ids": ["finance.default.v1"]}),
    )

    def fake_publish(project_root: Path, output_path: Path | None):
        steps.append(("publish", project_root, output_path))
        return {
            "release_id": "semantic_release.default",
            "release_version": "2026-04-03.v1",
            "projection_ids": ["finance.default.v1"],
            "fingerprint": "fingerprint",
        }

    monkeypatch.setattr(source_operations, "publish_semantic_release", fake_publish)

    response = source_operations.export_semantic_release(
        tmp_project_root,
        {"output_path": str(export_path)},
    )

    _assert_hint_envelope(response)
    assert steps == [
        ("validate", tmp_project_root),
        ("compile", tmp_project_root),
        ("publish", tmp_project_root, export_path),
    ]
    assert response["artifacts"] == [{"label": "Release Bundle", "value": str(export_path)}]

def test_export_semantic_release_uses_locale_stamped_default_path(tmp_project_root: Path) -> None:
    response = source_operations.export_semantic_release(
        tmp_project_root,
        {"target_locale": "en"},
    )
    release_path = Path(response["output_path"])
    payload = json.loads(release_path.read_text(encoding="utf-8"))

    assert response["runtime_locale"] == "en"
    assert response["locale_resolution"] == {"runtime_locale": "en", "source": "explicit_target_locale"}
    assert release_path.name == "semantic_release.default__2026-03-28.v6__en.json"
    assert payload["runtime_locale"] == "en"
    assert payload["master_taxonomy_release_id"].startswith("sha256:")
