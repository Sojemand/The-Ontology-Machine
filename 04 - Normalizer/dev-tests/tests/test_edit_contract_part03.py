from tests.edit_contract_shared import *  # noqa: F401,F403


def test_compile_release_package_reports_explicit_locale_without_rewriting_default_assets(tmp_project_root: Path) -> None:
    master_text_path = (
        tmp_project_root
        / "config"
        / "taxonomy_sources"
        / "semantic_release.default"
        / "master.text.en.yaml"
    )
    master_before = master_text_path.read_text(encoding="utf-8")

    compiled = source_operations.compile_release_package(tmp_project_root, {"target_locale": "en"})

    assert compiled["status"] == "ok"
    assert compiled["runtime_locale"] == "en"
    assert compiled["locale_resolution"] == {"runtime_locale": "en", "source": "explicit_target_locale"}
    assert compiled.get("artifacts") in (None, [])
    assert master_text_path.read_text(encoding="utf-8") == master_before


def test_validate_surface_rebuilds_compiled_release_draft(tmp_project_root: Path) -> None:
    from normalizer_vision.edit_contract.taxonomy_release_draft import load_release_copy
    from normalizer_vision.semantic_release import build_semantic_release

    artifact_root = tmp_project_root / "Artifact Tree"
    release_path = artifact_root / "Semantic Release" / "releases" / "semantic_release.default" / "release.json"
    release_path.parent.mkdir(parents=True)
    release_path.write_text(json.dumps(build_semantic_release(tmp_project_root), indent=2), encoding="utf-8")
    draft = load_release_copy(artifact_root, release_path)
    draft["release"]["projection_ids"] = []

    validated = _run_contract(
        tmp_project_root,
        {
            "action": "validate_surface",
            "surface_id": "normalizer.taxonomy_release_draft",
            "value": draft,
        },
    )

    assert validated["status"] == "ok"
    assert validated["value"]["verification"]["status"] == "verified"
    assert validated["value"]["release"]["projection_ids"] == sorted(
        [item["projection_id"] for item in validated["value"]["release"]["projections"]],
        key=lambda item: (item.casefold(), item),
    )
    assert "finance.default.v1" in validated["value"]["release"]["projection_ids"]
    assert validated["value"]["release"]["runtime_semantic_assets"]["release_fingerprint"] == validated["value"]["release"]["fingerprint"]


def test_source_authoring_surfaces_validate_current_values(tmp_project_root: Path) -> None:
    for surface_id in (
        "normalizer.taxonomy_master",
        "normalizer.taxonomy_profiles",
        "normalizer.translation_glossary",
        "normalizer.semantic_release_authoring",
    ):
        current = _run_contract(tmp_project_root, {"action": "read_surface", "surface_id": surface_id})
        response = _run_contract(
            tmp_project_root,
            {
                "action": "validate_surface",
                "surface_id": surface_id,
                "value": current["value"],
            },
        )

        assert response["status"] == "ok"
        assert isinstance(response["value"], dict)


def test_source_authoring_tool_actions_are_routed_by_edit_contract(tmp_project_root: Path) -> None:
    export_path = tmp_project_root / "output" / "contract-export.semantic_release.json"
    cases = (
        {"action": "list_master_terms"},
        {"action": "read_release_package"},
        {"action": "list_projections"},
        {"action": "read_projection", "projection_id": "finance.default.v1"},
        {"action": "set_locale_text", "locale": "en", "target_type": "master_package", "description": "Updated source package."},
        {"action": "preview_impact"},
        {"action": "validate_release_package"},
        {"action": "compile_release_package", "target_locale": "en"},
        {"action": "export_semantic_release", "target_locale": "en", "output_path": str(export_path)},
    )
    for payload in cases:
        response = _run_contract(tmp_project_root, payload)

        assert response["status"] == "ok"


def test_db_update_decision_recommends_auto_refill_for_compatible_stale_db(tmp_project_root: Path) -> None:
    import sqlite3

    from normalizer_vision.edit_contract.taxonomy_release_draft import db_update_decision
    from normalizer_vision.semantic_release import build_semantic_release

    release = build_semantic_release(tmp_project_root)
    db_path = tmp_project_root / "output" / "compatible.corpus.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE documents (id TEXT PRIMARY KEY, is_archived INTEGER DEFAULT 0);
        CREATE TABLE installation_state (singleton INTEGER PRIMARY KEY, active_snapshot_id TEXT, master_taxonomy_release_id TEXT);
        CREATE TABLE document_processing_state (document_id TEXT, projection_id TEXT, materialization_state TEXT, materialized_snapshot_id TEXT);
        CREATE TABLE document_payloads (document_id TEXT, projection_json TEXT);
        """
    )
    conn.execute("INSERT INTO documents (id, is_archived) VALUES ('doc-1', 0)")
    conn.execute(
        "INSERT INTO installation_state (singleton, active_snapshot_id, master_taxonomy_release_id) VALUES (1, 'snapshot-current', ?)",
        (release["master_taxonomy_release_id"],),
    )
    conn.execute(
        "INSERT INTO document_processing_state (document_id, projection_id, materialization_state, materialized_snapshot_id) VALUES ('doc-1', ?, 'stale', 'old-snapshot')",
        (release["projection_ids"][0],),
    )
    conn.execute(
        "INSERT INTO document_payloads (document_id, projection_json) VALUES ('doc-1', ?)",
        (json.dumps({"master_taxonomy_id": release["master_taxonomy_id"]}),),
    )
    conn.commit()
    conn.close()

    decision = db_update_decision(db_path, release)

    assert decision["status"] == "update_current_db"
    assert decision["recommended_action"] == "update_current_db_with_auto_refill"
    assert decision["auto_refill"] is True


def test_db_update_decision_requires_new_db_for_different_master_line(tmp_project_root: Path) -> None:
    import sqlite3

    from normalizer_vision.edit_contract.taxonomy_release_draft import db_update_decision
    from normalizer_vision.semantic_release import build_semantic_release

    release = build_semantic_release(tmp_project_root)
    db_path = tmp_project_root / "output" / "foreign-master.corpus.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE documents (id TEXT PRIMARY KEY, is_archived INTEGER DEFAULT 0);
        CREATE TABLE installation_state (singleton INTEGER PRIMARY KEY, active_snapshot_id TEXT, master_taxonomy_release_id TEXT);
        """
    )
    conn.execute("INSERT INTO documents (id, is_archived) VALUES ('doc-1', 0)")
    conn.execute(
        "INSERT INTO installation_state (singleton, active_snapshot_id, master_taxonomy_release_id) VALUES (1, 'snapshot-current', 'sha256:other-master-line')"
    )
    conn.commit()
    conn.close()

    decision = db_update_decision(db_path, release)

    assert decision["status"] == "new_db_required"
    assert decision["recommended_action"] == "materialize_new_db"


def test_db_update_decision_uses_readonly_bounded_sqlite_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sqlite3

    from normalizer_vision.edit_contract import taxonomy_release_draft

    db_path = tmp_path / "corpus.db"
    db_path.write_bytes(b"")
    captured: dict[str, object] = {}

    def fake_connect(database: str, **kwargs):
        captured["database"] = database
        captured["kwargs"] = kwargs
        raise sqlite3.OperationalError("probe stop")

    monkeypatch.setattr(taxonomy_release_draft.sqlite3, "connect", fake_connect)

    with pytest.raises(sqlite3.OperationalError, match="probe stop"):
        taxonomy_release_draft._connect_corpus_db_readonly(db_path)

    assert str(captured["database"]).startswith("file:")
    assert str(captured["database"]).endswith("?mode=ro")
    assert captured["kwargs"] == {"uri": True, "timeout": 5.0}
