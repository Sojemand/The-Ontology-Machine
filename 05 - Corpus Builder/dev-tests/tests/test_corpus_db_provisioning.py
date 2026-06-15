from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from corpus_builder.context import ModuleContext
from corpus_builder.services.corpus_db_provisioning import (
    create_and_activate_new_corpus_db,
    persist_default_corpus_db_path,
    provision_new_corpus_db_path,
    resolve_existing_corpus_db_path,
)


def _make_context(tmp_path: Path, *, with_orchestrator_state: bool = True) -> ModuleContext:
    module_root = tmp_path / "05 - Corpus Builder"
    context = ModuleContext(module_root)
    context.ensure_runtime_dirs()
    context.config_dir.mkdir(parents=True, exist_ok=True)
    context.config_path.write_text(
        json.dumps(
            {
                "database": {"corpus_db": str((tmp_path / "Artefacts" / "Corpus" / "corpus.db").resolve())},
                "embeddings": {
                    "dimensions": 1536,
                    "batch_size": 50,
                    "max_text_chars": 12000,
                },
                "archive": {"enabled": True, "keep_archived": True},
                "fts": {"enabled": True, "tokenizer": "unicode61"},
                "source": {"page_images_dir": "", "persist_page_images_in_db": False},
                "semantic": {
                    "published_release_path": "./config/semantic_release.default.json",
                    "active_release_path": "./state/semantic_release.active.json",
                    "release_report_path": "./state/semantic_release_report.json",
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if with_orchestrator_state:
        orchestrator_state = tmp_path / "00 - Orchestrator" / "state"
        orchestrator_state.mkdir(parents=True, exist_ok=True)
        (orchestrator_state / "ui_state.json").write_text(
            json.dumps(
                {
                    "artifact_folder": str((tmp_path / "Artefacts").resolve()),
                    "corpus_output_folder": str((tmp_path / "Artefacts" / "Corpus").resolve()),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return context


def test_create_and_activate_new_corpus_db_updates_default_path(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    release_path = tmp_path / "semantic_release.json"
    release_path.write_text("{}", encoding="utf-8")
    confirmation_path = tmp_path / "new-db-confirmation.json"
    confirmation_path.write_text(
        json.dumps(
            {
                "artifact_version": "new_corpus_db_confirmation_v1",
                "requested_action": "create_and_activate_new_corpus_db",
                "confirmed": True,
                "database_label": "Housing April",
                "taxonomy_locale": "en",
                "corpus_root": str((tmp_path / "Artefacts" / "Corpus").resolve()),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    captured: dict[str, str] = {}

    def fake_activate(_context, *, release_path=None, corpus_db_path=None):
        captured["release_path"] = str(release_path)
        captured["corpus_db_path"] = str(corpus_db_path)
        return {
            "status": "applied",
            "release_id": "semantic_release.default",
            "release_version": "v1",
            "active_snapshot_id": "sha256:test",
        }

    detail = create_and_activate_new_corpus_db(
        context,
        release_path=release_path,
        confirmation_artifact_path=confirmation_path,
        activate_release_fn=fake_activate,
    )

    expected_db_path = (tmp_path / "Artefacts" / "Corpus" / f"Housing-April-{date.today().isoformat()}-corpus-en.db").resolve()
    stored = json.loads(context.config_path.read_text(encoding="utf-8"))
    assert captured == {
        "release_path": str(release_path),
        "corpus_db_path": str(expected_db_path),
    }
    assert detail["corpus_db_path"] == str(expected_db_path)
    assert detail["previous_default_corpus_db_path"].endswith("Artefacts\\Corpus\\corpus.db")
    assert stored["database"]["corpus_db"] == str(expected_db_path)


def test_create_and_activate_new_corpus_db_rejects_missing_confirmation_artifact(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    release_path = tmp_path / "semantic_release.json"
    release_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Confirmation-Artefakt fehlt"):
        create_and_activate_new_corpus_db(
            context,
            release_path=release_path,
            confirmation_artifact_path=tmp_path / "missing-confirmation.json",
            activate_release_fn=lambda *_args, **_kwargs: {"status": "applied"},
        )


def test_create_and_activate_new_corpus_db_uses_confirmation_corpus_root_without_orchestrator_state(tmp_path: Path) -> None:
    context = _make_context(tmp_path, with_orchestrator_state=False)
    release_path = tmp_path / "semantic_release.json"
    release_path.write_text("{}", encoding="utf-8")
    explicit_root = tmp_path / "Explicit Corpus"
    confirmation_path = tmp_path / "new-db-confirmation.json"
    confirmation_path.write_text(
        json.dumps(
            {
                "artifact_version": "new_corpus_db_confirmation_v1",
                "requested_action": "create_and_activate_new_corpus_db",
                "confirmed": True,
                "database_label": "Housing April",
                "taxonomy_locale": "en",
                "corpus_root": str(explicit_root),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    detail = create_and_activate_new_corpus_db(
        context,
        release_path=release_path,
        confirmation_artifact_path=confirmation_path,
        activate_release_fn=lambda *_args, **_kwargs: {"status": "applied"},
    )

    expected_db_path = explicit_root.resolve() / f"Housing-April-{date.today().isoformat()}-corpus-en.db"
    assert detail["corpus_root"] == str(explicit_root.resolve())
    assert detail["corpus_db_path"] == str(expected_db_path)


def test_provision_new_corpus_db_path_requires_explicit_corpus_root(tmp_path: Path) -> None:
    context = _make_context(tmp_path)

    with pytest.raises(ValueError, match="corpus_root"):
        provision_new_corpus_db_path(context, database_label="Housing April", taxonomy_locale="en")


def test_provision_new_corpus_db_path_fails_when_target_exists(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    corpus_root = tmp_path / "Artefacts" / "Corpus"
    target = provision_new_corpus_db_path(context, database_label="Housing April", taxonomy_locale="en", corpus_root=corpus_root)
    Path(target["corpus_db_path"]).parent.mkdir(parents=True, exist_ok=True)
    Path(target["corpus_db_path"]).write_text("db", encoding="utf-8")

    with pytest.raises(ValueError, match="existiert bereits"):
        provision_new_corpus_db_path(context, database_label="Housing April", taxonomy_locale="en", corpus_root=corpus_root)


def test_provision_new_corpus_db_path_bounds_generated_filename(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    long_label = "Housing With An Exceptionally Long Label " * 8
    long_locale = "de-DE-tenant-locale-" * 4

    target = provision_new_corpus_db_path(
        context,
        database_label=long_label,
        taxonomy_locale=long_locale,
        corpus_root=tmp_path / "Artefacts" / "Corpus",
    )

    db_name = Path(target["corpus_db_path"]).name
    assert len(db_name) <= 128
    assert db_name.endswith(".db")
    assert f"-{date.today().isoformat()}-corpus-" in db_name
    assert target["database_label"] == long_label.strip()


def test_persist_default_corpus_db_path_rejects_malformed_config_without_overwrite(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    context.config_path.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="kein gueltiges JSON"):
        persist_default_corpus_db_path(context, tmp_path / "new.db")

    assert context.config_path.read_text(encoding="utf-8") == "{"


def test_resolve_existing_corpus_db_path_rejects_missing_db(tmp_path: Path) -> None:
    context = _make_context(tmp_path)

    with pytest.raises(ValueError, match="existiert nicht"):
        resolve_existing_corpus_db_path(context, tmp_path / "missing.corpus.db")
