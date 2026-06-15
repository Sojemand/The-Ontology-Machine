from tests.edit_contract_shared import *  # noqa: F401,F403


def test_activate_semantic_release_exports_and_delegates_to_corpus_builder(monkeypatch, tmp_project_root: Path) -> None:
    export_path = tmp_project_root / "output" / "semantic_release.activated.json"
    corpus_db_path = tmp_project_root / "output" / "corpus.db"
    captured = {}
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
        assert project_root == tmp_project_root
        assert output_path == export_path
        output_path.write_text("{}", encoding="utf-8")
        return {
            "release_id": "semantic_release.default",
            "release_version": "2026-04-03.v1",
            "projection_ids": ["finance.default.v1"],
            "fingerprint": "fingerprint",
        }

    def fake_activate(project_root: Path, *, release_path: str, corpus_db_path: str):
        captured["project_root"] = project_root
        captured["release_path"] = release_path
        captured["corpus_db_path"] = corpus_db_path
        return {"status": "ok", "message": "activated"}

    monkeypatch.setattr(source_operations, "publish_semantic_release", fake_publish)
    monkeypatch.setattr(source_operations.corpus_proxy, "activate_release", fake_activate)

    response = source_operations.activate_semantic_release(
        tmp_project_root,
        {"release_path": str(export_path), "corpus_db_path": str(corpus_db_path)},
    )

    _assert_hint_envelope(response)
    assert export_path.exists()
    assert steps == [
        ("validate", tmp_project_root),
        ("compile", tmp_project_root),
        ("publish", tmp_project_root, export_path),
    ]
    assert captured == {
        "project_root": tmp_project_root,
        "release_path": str(export_path),
        "corpus_db_path": str(corpus_db_path),
    }
    assert response["required_fields"] == ["release_path", "corpus_db_path"]
    assert response["artifacts"] == [
        {"label": "Release Bundle", "value": str(export_path)},
        {"label": "Corpus DB", "value": str(corpus_db_path)},
    ]


def test_create_and_activate_new_corpus_db_exports_and_delegates_to_corpus_builder(monkeypatch, tmp_project_root: Path) -> None:
    export_path = tmp_project_root / "output" / "semantic_release.activated.json"
    confirmation_path = tmp_project_root / "state" / "new-db-confirmation.json"
    confirmation_path.parent.mkdir(parents=True, exist_ok=True)
    confirmation_path.write_text(
        json.dumps(
            {
                "artifact_version": "new_corpus_db_confirmation_v1",
                "requested_action": "create_and_activate_new_corpus_db",
                "confirmed": True,
                "database_label": "Wohnen",
                "taxonomy_locale": "en",
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    captured = {}
    steps: list[object] = []

    monkeypatch.setattr(
        source_operations,
        "validate_release_package",
        lambda root, payload=None: steps.append(("validate", root, payload)) or {"status": "ok"},
    )
    monkeypatch.setattr(
        source_operations,
        "ensure_compiled_taxonomy_assets",
        lambda root, target_locale=None: steps.append(("compile", root, target_locale)) or SimpleNamespace(release={"projection_ids": ["finance.default.v1"]}),
    )

    def fake_publish(project_root: Path, output_path: Path | None, target_locale: str | None = None):
        steps.append(("publish", project_root, output_path, target_locale))
        assert project_root == tmp_project_root
        assert output_path == export_path
        output_path.write_text("{}", encoding="utf-8")
        return {
            "release_id": "semantic_release.default",
            "release_version": "2026-04-03.v1",
            "projection_ids": ["finance.default.v1"],
            "fingerprint": "fingerprint",
            "runtime_locale": "en",
        }

    def fake_activate(project_root: Path, *, release_path: str, confirmation_artifact_path: str):
        captured["project_root"] = project_root
        captured["release_path"] = release_path
        captured["confirmation_artifact_path"] = confirmation_artifact_path
        return {
            "status": "ok",
            "corpus_db_path": str(tmp_project_root / "Artefacts" / "Corpus" / "wohnen-2026-04-05-corpus-en.db"),
            "previous_default_corpus_db_path": str(tmp_project_root / "Artefacts" / "Corpus" / "corpus.db"),
        }

    monkeypatch.setattr(source_operations, "publish_semantic_release", fake_publish)
    monkeypatch.setattr(source_operations.corpus_proxy, "create_and_activate_new_corpus_db", fake_activate)

    response = source_operations.create_and_activate_new_corpus_db(
        tmp_project_root,
        {"release_path": str(export_path), "confirmation_artifact_path": str(confirmation_path)},
    )

    _assert_hint_envelope(response)
    assert export_path.exists()
    assert steps == [
        ("validate", tmp_project_root, {"target_locale": "en"}),
        ("compile", tmp_project_root, "en"),
        ("publish", tmp_project_root, export_path, "en"),
    ]
    assert captured == {
        "project_root": tmp_project_root,
        "release_path": str(export_path),
        "confirmation_artifact_path": str(confirmation_path),
    }
    assert response["required_fields"] == ["release_path", "confirmation_artifact_path"]
    assert response["artifacts"] == [
        {"label": "Release Bundle", "value": str(export_path)},
        {"label": "Corpus DB", "value": str(tmp_project_root / "Artefacts" / "Corpus" / "wohnen-2026-04-05-corpus-en.db")},
    ]
