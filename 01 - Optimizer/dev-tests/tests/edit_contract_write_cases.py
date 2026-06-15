from __future__ import annotations

from pathlib import Path

from edit_contract_support import _run_contract


def test_settings_roundtrip_uses_seeded_app_home_config(tmp_path: Path) -> None:
    current = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "optimizer.settings"})
    assert current["value"]["parallel_workers"] == 4
    assert current["value"]["render_dpi"] == 150
    assert current["value"]["render_width_px"] == 1240
    written = _run_contract(
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "optimizer.settings",
            "value": {**current["value"], "parallel_workers": "2", "plugin_timeout_seconds": "90", "render_dpi": "180"},
        },
    )
    assert written["value"]["parallel_workers"] == 2
    assert written["value"]["render_dpi"] == 180
    reread = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "optimizer.settings"})
    assert reread["value"]["parallel_workers"] == 2
    assert reread["value"]["plugin_timeout_seconds"] == 90
    assert reread["value"]["render_dpi"] == 180


def test_ocr_prompt_roundtrip_uses_owner_config_file(tmp_path: Path) -> None:
    current = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "optimizer.ocr_prompt"})
    assert current["status"] == "ok"
    assert "{page_count}" in current["value"]["ocr_prompt_md"]
    updated_prompt = current["value"]["ocr_prompt_md"] + "\nPrefer preserving line breaks."
    written = _run_contract(
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "optimizer.ocr_prompt",
            "value": {"ocr_prompt_md": updated_prompt},
        },
    )
    assert written["status"] == "ok"
    assert "Prefer preserving line breaks." in written["value"]["ocr_prompt_md"]
    reread = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "optimizer.ocr_prompt"})
    assert reread["value"]["ocr_prompt_md"] == written["value"]["ocr_prompt_md"]
