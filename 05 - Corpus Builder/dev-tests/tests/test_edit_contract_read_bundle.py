from __future__ import annotations

from pathlib import Path

from .test_edit_contract import _copy_module, _invoke_contract


def test_read_bundle_returns_same_surface_set_with_values(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    described = _invoke_contract(module_root, tmp_path, {"action": "describe_surfaces"})
    bundled = _invoke_contract(module_root, tmp_path, {"action": "read_bundle"})

    assert bundled["status"] == "ok"
    assert bundled["module_summary"] == described["module_summary"]
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])
    assert [card["label"] for card in bundled["summary_cards"]] == [card["label"] for card in described["summary_cards"]]
