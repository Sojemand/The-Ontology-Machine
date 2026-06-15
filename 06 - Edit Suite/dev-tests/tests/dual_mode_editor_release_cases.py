from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from edit_suite import validation
from edit_suite.ui import taxonomy_release_editor

from dual_mode_editor_support import Entry, Var


def test_taxonomy_release_scan_finds_canonical_release(tmp_path) -> None:
    release_path = tmp_path / "Semantic Release" / "releases" / "semantic_release.default" / "release.json"
    release_path.parent.mkdir(parents=True)
    release_path.write_text(
        """
        {
          "release_id": "semantic_release.default",
          "release_version": "1",
          "fingerprint": "sha256:test",
          "projection_ids": [],
          "master_taxonomy": {},
          "projections": []
        }
        """,
        encoding="utf-8",
    )

    candidates = taxonomy_release_editor._scan_release_candidates(str(tmp_path))

    assert len(candidates) == 1
    assert candidates[0]["canonical"] is True
    assert candidates[0]["path"] == str(release_path.resolve(strict=False))


def test_taxonomy_release_load_copy_reads_selected_release(monkeypatch, tmp_path) -> None:
    release_path = tmp_path / "Semantic Release" / "releases" / "semantic_release.default" / "release.json"
    release_path.parent.mkdir(parents=True)
    release_path.write_text(
        """
        {
          "release_id": "semantic_release.default",
          "release_version": "1",
          "fingerprint": "sha256:test",
          "projection_ids": ["finance.default.v1"],
          "master_taxonomy_release_id": "sha256:master",
          "master_taxonomy": {},
          "projections": []
        }
        """,
        encoding="utf-8",
    )
    widget = SimpleNamespace(
        _draft={"release_candidates": [], "verification": {}},
        _candidate_var=Var("Release"),
        _candidate_labels={"Release": str(release_path)},
        _artifact_root_entry=Entry(str(tmp_path)),
        _working_release_entry=Entry(""),
    )
    monkeypatch.setattr(taxonomy_release_editor, "_refresh_all", lambda _widget: None)

    taxonomy_release_editor._load_selected_release(widget)

    assert widget._draft["selected_release_path"] == str(release_path)
    assert widget._draft["working_release_path"].endswith("Semantic Release\\drafts\\edit_suite\\semantic_release.default\\release.json")
    assert widget._draft["release"]["release_id"] == "semantic_release.default"
    assert widget._draft["verification"]["status"] == "draft_loaded"


def test_taxonomy_release_working_copy_path_caps_long_release_id(tmp_path) -> None:
    path = taxonomy_release_editor._default_working_release_path(
        str(tmp_path),
        {"release_id": "semantic-release-" * 30},
    )
    release_dir = Path(path).parent

    assert len(release_dir.name) <= validation.MAX_SAFE_FILENAME_LENGTH
    assert Path(path).name == "release.json"
