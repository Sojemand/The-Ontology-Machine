from __future__ import annotations

from .test_edit_contract import _run_contract


def test_read_bundle_returns_same_surface_set_with_values(tmp_project_root) -> None:
    described = _run_contract(tmp_project_root, {"action": "describe_surfaces"})
    bundled = _run_contract(tmp_project_root, {"action": "read_bundle"})

    assert bundled["status"] == "ok"
    assert bundled["module_summary"] == described["module_summary"]
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])
