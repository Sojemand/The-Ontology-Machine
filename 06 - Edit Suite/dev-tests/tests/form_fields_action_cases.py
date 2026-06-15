from __future__ import annotations

from types import SimpleNamespace

from edit_suite import validation
from edit_suite.ui import action_forms

from form_fields_support import _PathEntry, _Var


def test_choose_path_prefills_export_save_dialog_from_format(tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    app = SimpleNamespace(_selected_entry=lambda: SimpleNamespace(module_root=str(tmp_path)))
    entry = _PathEntry("")
    captured = {}

    def fake_save_dialog(**kwargs):
        captured.update(kwargs)
        return str(output_dir / "export.csv")

    monkeypatch.setattr(action_forms.fd, "asksaveasfilename", fake_save_dialog)

    action_forms._choose_path(
        app,
        entry,
        "save_file",
        spec={"name": "output_path", "label": "Export File"},
        widgets={"fmt": {"kind": "select", "variable": _Var("csv")}},
    )

    assert captured["initialdir"] == str(output_dir)
    assert captured["initialfile"] == "export.csv"
    assert captured["defaultextension"] == ".csv"
    assert captured["filetypes"][0] == ("CSV", "*.csv")
    assert entry.get() == str(output_dir / "export.csv")


def test_choose_path_prefills_save_dialog_from_existing_file_path(tmp_path, monkeypatch) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    app = SimpleNamespace(_selected_entry=lambda: SimpleNamespace(module_root=str(tmp_path)))
    entry = _PathEntry(str(export_dir / "release.json"))
    captured = {}

    def fake_save_dialog(**kwargs):
        captured.update(kwargs)
        return str(export_dir / "release.v2.json")

    monkeypatch.setattr(action_forms.fd, "asksaveasfilename", fake_save_dialog)

    action_forms._choose_path(
        app,
        entry,
        "save_file",
        spec={"name": "release_path", "label": "Release Path"},
        widgets={},
    )

    assert captured["initialdir"] == str(export_dir)
    assert captured["initialfile"] == "release.json"
    assert captured["defaultextension"] == ".json"
    assert captured["filetypes"][0] == ("JSON", "*.json")
    assert entry.get() == str(export_dir / "release.v2.json")


def test_choose_path_caps_default_save_dialog_seed_filename(tmp_path, monkeypatch) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    app = SimpleNamespace(_selected_entry=lambda: SimpleNamespace(module_root=str(tmp_path)))
    entry = _PathEntry("")
    captured = {}

    def fake_save_dialog(**kwargs):
        captured.update(kwargs)
        return str(export_dir / "release.v2.json")

    monkeypatch.setattr(action_forms.fd, "asksaveasfilename", fake_save_dialog)

    action_forms._choose_path(
        app,
        entry,
        "save_file",
        spec={"name": "release_path", "default": str(export_dir / (("owner-default-name-" * 30) + ".json"))},
        widgets={},
    )

    assert captured["initialdir"] == str(export_dir)
    assert len(captured["initialfile"]) <= validation.MAX_SAFE_FILENAME_LENGTH
    assert captured["initialfile"].endswith(".json")


def test_choose_path_caps_owner_suggested_save_dialog_filename(tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    app = SimpleNamespace(_selected_entry=lambda: SimpleNamespace(module_root=str(tmp_path)))
    entry = _PathEntry("")
    captured = {}

    def fake_save_dialog(**kwargs):
        captured.update(kwargs)
        return str(output_dir / "export.json")

    monkeypatch.setattr(action_forms.fd, "asksaveasfilename", fake_save_dialog)

    action_forms._choose_path(
        app,
        entry,
        "save_file",
        spec={"name": "export " + ("very long owner field " * 20)},
        widgets={"fmt": {"kind": "select", "variable": _Var("json")}},
    )

    assert len(captured["initialfile"]) <= validation.MAX_SAFE_FILENAME_LENGTH
    assert captured["initialfile"].endswith(".json")
