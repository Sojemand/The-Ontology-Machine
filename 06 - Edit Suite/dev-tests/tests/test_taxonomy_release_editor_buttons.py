from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from edit_suite.ui import taxonomy_release_editor

from button_evidence_support import buttons, invoke, invoke_button, surface, tk_root


def test_taxonomy_release_editor_buttons_mutate_draft_and_trigger_verify(monkeypatch, tmp_path: Path, tk_root) -> None:
    release_path = tmp_path / "Semantic Release" / "releases" / "semantic_release.default" / "release.json"
    release_path.parent.mkdir(parents=True)
    release_path.write_text(json.dumps(_release_fixture(), indent=2), encoding="utf-8")
    corpus_db = tmp_path / "corpus.db"
    corpus_db.write_bytes(b"")
    monkeypatch.setattr(taxonomy_release_editor.fd, "askdirectory", lambda **_kwargs: str(tmp_path))
    monkeypatch.setattr(taxonomy_release_editor.fd, "askopenfilename", lambda **_kwargs: str(corpus_db))
    monkeypatch.setattr(taxonomy_release_editor.background_jobs, "start", _run_background_immediately)
    events: list[tuple[str, str]] = []
    app = SimpleNamespace(validate_surface=lambda surface_id: events.append(("verify", surface_id)))
    model = surface(
        surface_id="normalizer.taxonomy_release_draft",
        editor_kind="taxonomy_release_draft",
        descriptor={},
        draft={"schema_version": taxonomy_release_editor.SCHEMA_VERSION, "release": {}},
    )
    frame = taxonomy_release_editor.render(tk_root, model, app=app)
    frame.grid(row=0, column=0)

    invoke(frame, "Browse", index=0)
    assert frame._draft["artifact_root"] == str(tmp_path)
    assert frame._draft["release_candidates"][0]["path"] == str(release_path.resolve(strict=False))
    invoke(frame, "Scan")

    invoke(frame, "Load Copy")
    assert frame._draft["release"]["release_id"] == "semantic_release.default"
    assert frame._working_release_entry.get().endswith("Semantic Release\\drafts\\edit_suite\\semantic_release.default\\release.json")
    invoke_button(buttons(frame._taxonomy_list)[0])
    invoke_button(buttons(frame._projection_list)[0])

    invoke(frame, "Browse", index=1)
    assert frame._corpus_db_entry.get() == str(corpus_db)

    domain_count = len(taxonomy_release_editor._taxonomy_items(frame, "domains"))
    invoke(frame, "New", index=0)
    assert len(taxonomy_release_editor._taxonomy_items(frame, "domains")) == domain_count + 1
    invoke(frame, "Duplicate", index=0)
    assert len(taxonomy_release_editor._taxonomy_items(frame, "domains")) == domain_count + 2
    invoke(frame, "Delete", index=0)
    assert len(taxonomy_release_editor._taxonomy_items(frame, "domains")) == domain_count + 1

    projection_count = len(taxonomy_release_editor._projections(frame))
    invoke(frame, "New", index=1)
    assert len(taxonomy_release_editor._projections(frame)) == projection_count + 1
    invoke(frame, "Duplicate", index=1)
    assert len(taxonomy_release_editor._projections(frame)) == projection_count + 2
    invoke(frame, "Delete", index=1)
    assert len(taxonomy_release_editor._projections(frame)) == projection_count + 1
    invoke(frame, "Update Choices")
    assert "domain_ids" in frame._projection_pickers

    invoke(frame, "Verify")
    assert events == [("verify", model.surface_id)]


def _release_fixture() -> dict:
    return {
        "release_id": "semantic_release.default",
        "release_version": "1",
        "fingerprint": "sha256:test",
        "projection_ids": ["finance.default.v1"],
        "master_taxonomy": {
            "domains": [{"id": "finance", "label": "Finance"}],
            "document_types": [{"code": "invoice", "label": "Invoice"}],
            "categories": [{"code": "finance"}],
            "subcategories": [{"code": "invoice"}],
            "field_codes": [{"code": "issuer"}],
            "row_types": [],
            "cell_codes": [],
            "role_types": [{"code": "issuer"}],
        },
        "projections": [
            {
                "projection_id": "finance.default.v1",
                "label": "Finance",
                "description": "",
                "domain_ids": ["finance"],
                "include_document_types": ["invoice"],
                "include_categories": ["finance"],
                "include_subcategories": ["invoice"],
                "include_field_codes": ["issuer"],
                "include_row_types": [],
                "include_cell_codes": [],
                "routing": {
                    "when_to_use": "",
                    "avoid_when": "",
                    "example_document_types": ["invoice"],
                    "surface_signals": {"text_markers": [], "domain_markers": {}, "section_roles": [], "party_roles": []},
                },
            }
        ],
    }


def _run_background_immediately(_app, *, work, deliver) -> None:
    try:
        deliver(work(), None)
    except Exception as exc:
        deliver(None, exc)
